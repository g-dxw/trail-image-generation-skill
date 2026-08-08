from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from detect_checkpoint_candidates import detect_candidates, parse_kml_bytes  # noqa: E402


def point(lon: float, lat: float, minute: int | None = None) -> dict:
    return {
        "lon": lon,
        "lat": lat,
        "ele": 800.0,
        "time": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute) if minute is not None else None,
    }


class CheckpointCandidateTests(unittest.TestCase):
    def test_photo_density_is_high_priority(self):
        track = [point(107.0 + i * 0.0001, 29.0, i) for i in range(8)]
        photos = [point(107.0003, 29.0, 3) | {"name": f"照片{i}"} for i in range(5)]
        result = detect_candidates(track, photos, progress_window_m=20, min_score=0.2)
        self.assertTrue(result["candidates"])
        self.assertTrue(any(c["photo_count"] >= 5 for c in result["candidates"]))
        self.assertTrue(any(c["review_priority"] == "high" for c in result["candidates"]))

    def test_backtracking_without_timestamps_does_not_fake_dwell(self):
        track = [point(107.0, 29.0), point(107.0003, 29.0), point(107.0006, 29.0), point(107.0003, 29.0), point(107.0, 29.0)]
        result = detect_candidates(track, min_score=0.2)
        self.assertTrue(any(c["signals"]["local_backtracking"] > 0 for c in result["candidates"]))
        self.assertTrue(all(c["signals"]["dwell"] == 0 for c in result["candidates"]))

    def test_named_point_gets_high_priority(self):
        track = [point(107.0 + i * 0.0001, 29.0, i) for i in range(6)]
        named = [{"name": "图腾", "lon": 107.0002, "lat": 29.0}]
        result = detect_candidates(track, named_points=named, min_score=0.2)
        self.assertTrue(any(c["temporary_name"] == "图腾" and c["source_named"] for c in result["candidates"]))

    def test_kml_photo_fields_are_parsed(self):
        xml = b'''<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
        <Placemark><name>route</name><LineString><coordinates>107,29,800 107.001,29,801 107.002,29,802</coordinates></LineString></Placemark>
        <Placemark><description>&lt;img src="x.jpg"/&gt;</description><when>2026-01-01T00:00:00Z</when><Point><coordinates>107.001,29,801</coordinates></Point></Placemark>
        </Document></kml>'''
        track, photos, _ = parse_kml_bytes(xml)
        self.assertEqual(len(track), 3)
        self.assertEqual(len(photos), 1)
        self.assertIsNotNone(photos[0]["time"])

    def test_metadata_labeled_first_keeps_unlabeled_for_hotspot_only(self):
        track = [point(107.0 + i * 0.0001, 29.0, i) for i in range(8)]
        photos = [point(107.0003, 29.0, 3) | {"name": f"照片{i}"} for i in range(4)]
        photos.append(point(107.0007, 29.0, 7) | {"name": "远处照片"})
        photos.append(point(107.0003, 29.0, 3) | {"name": "图腾", "label_source": "kml_name"})
        result = detect_candidates(track, photos, progress_window_m=20, min_score=0.99)
        self.assertEqual(result["photo_analysis_policy"]["mode"], "metadata_labeled_first")
        self.assertEqual(result["photo_analysis_policy"]["labeled_photo_count"], 1)
        self.assertEqual(result["photo_analysis_policy"]["hotspot_photo_count"], 0)
        self.assertTrue(any(p["analysis_status"] == "unlabeled" for p in result["photos"]))

    def test_selected_mode_can_restore_specific_photo_analysis(self):
        track = [point(107.0 + i * 0.0001, 29.0, i) for i in range(5)]
        photos = [point(107.0002, 29.0, 2) | {"name": "照片A", "file_id": "A"}, point(107.0003, 29.0, 3) | {"name": "照片B", "file_id": "B"}]
        result = detect_candidates(track, photos, analysis_mode="selected", selected_photo_ids={"B"}, min_score=0.2)
        statuses = {p["photo_id"]: p["analysis_status"] for p in result["photos"]}
        self.assertEqual(statuses["照片A"], "skipped")
        self.assertEqual(statuses["照片B"], "selected")


if __name__ == "__main__":
    unittest.main()
