from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from route_intensity import (  # noqa: E402
    calculate_for_source,
    classify_intensity,
    compute_route_intensity,
)


KML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    {extended}
    <Placemark><LineString><coordinates>
      107.0000,29.0000,700 107.0100,29.0000,710 107.0200,29.0000,705
    </coordinates></LineString></Placemark>
  </Document>
</kml>
"""

EXTENDED = """
<ExtendedData>
  <Data name="Distance"><value>10000</value></Data>
  <Data name="ElevationGain"><value>500</value></Data>
  <Data name="ElevationLoss"><value>400</value></Data>
</ExtendedData>
"""

GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk><trkseg>
    <trkpt lat="29.0000" lon="107.0000"><ele>700</ele></trkpt>
    <trkpt lat="29.0000" lon="107.0100"><ele>710</ele></trkpt>
    <trkpt lat="29.0000" lon="107.0200"><ele>705</ele></trkpt>
  </trkseg></trk>
</gpx>
"""

GPX_NO_ELEVATION = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk><trkseg>
    <trkpt lat="29.0000" lon="107.0000" />
    <trkpt lat="29.0000" lon="107.0100" />
  </trkseg></trk>
</gpx>
"""


class RouteIntensityTests(unittest.TestCase):
    def test_fixed_formula_example(self):
        result = compute_route_intensity(
            distance_km=10.0,
            gain_m=500.0,
            loss_m=400.0,
            average_elevation_m=1000.0,
        )
        expected_load = 4 + 10 / 10 * 0.5 + 500 / 1000 * 0.5
        expected_factor = 1 + 1000 / 5500
        expected_raw = (10 / 10 + 500 / 1000 + 400 / 1000) * expected_load / 10 * expected_factor
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["raw_score"], expected_raw, places=6)
        self.assertEqual(result["score"], 1.1)
        self.assertEqual(result["level"], "休闲强度")

    def test_classification_boundaries(self):
        expected = {
            1.5: "休闲强度",
            1.6: "初级强度",
            3.0: "初级强度",
            3.1: "中级强度",
            5.0: "中级强度",
            5.1: "大强度",
            8.0: "大强度",
            8.1: "超大强度",
        }
        for score, level in expected.items():
            with self.subTest(score=score):
                self.assertEqual(classify_intensity(score), level)

    def test_source_metadata_precedes_calculated_track(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.kml"
            source.write_text(KML_TEMPLATE.format(extended=EXTENDED), encoding="utf-8")
            result = calculate_for_source(source)
        self.assertEqual(result["inputs"]["distance_km"], {"value": 10.0, "source": "source_metadata"})
        self.assertEqual(result["inputs"]["elevation_gain_m"], {"value": 500.0, "source": "source_metadata"})
        self.assertEqual(result["inputs"]["elevation_loss_m"], {"value": 400.0, "source": "source_metadata"})

    def test_cli_override_precedes_source_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.kml"
            source.write_text(KML_TEMPLATE.format(extended=EXTENDED), encoding="utf-8")
            result = calculate_for_source(source, distance_km=12.0, gain_m=600.0, loss_m=550.0)
        self.assertEqual(result["inputs"]["distance_km"], {"value": 12.0, "source": "cli_override"})
        self.assertEqual(result["inputs"]["elevation_gain_m"]["source"], "cli_override")
        self.assertEqual(result["inputs"]["elevation_loss_m"]["source"], "cli_override")

    def test_gpx_falls_back_to_calculated_track(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.gpx"
            source.write_text(GPX, encoding="utf-8")
            result = calculate_for_source(source)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["inputs"]["distance_km"]["source"], "calculated_track")
        self.assertEqual(result["inputs"]["average_elevation_m"]["source"], "calculated_track")

    def test_missing_all_elevation_is_insufficient(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.gpx"
            source.write_text(GPX_NO_ELEVATION, encoding="utf-8")
            result = calculate_for_source(source)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["level"])

    def test_kmz_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.kmz"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("doc.kml", KML_TEMPLATE.format(extended=EXTENDED))
            result = calculate_for_source(source)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["inputs"]["distance_km"]["source"], "source_metadata")

    def test_inspect_kmz_embeds_route_intensity(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "route.kmz"
            output_dir = Path(folder) / "output"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("doc.kml", KML_TEMPLATE.format(extended=EXTENDED))
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL_DIR / "scripts" / "inspect_kmz.py"),
                    str(source),
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads((output_dir / "route-轨迹摘要.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["route_intensity"]["status"], "ok")
        self.assertEqual(summary["route_intensity"]["level"], "休闲强度")

    def test_result_is_json_serializable(self):
        result = compute_route_intensity(
            distance_km=10,
            gain_m=500,
            loss_m=400,
            average_elevation_m=None,
        )
        json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["altitude_factor"], 1.0)
        self.assertTrue(any("平均海拔" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
