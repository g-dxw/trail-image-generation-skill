#!/usr/bin/env python3
"""Build deterministic landmark review/final boards from approved simplified images."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover - exercised through subprocess tests
    raise SystemExit("Pillow is required: install it with `python3 -m pip install Pillow`") from exc


BOARD_SIZE = (2400, 1800)
MAX_ITEMS = 12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def grid_for(count: int) -> tuple[int, int]:
    if count <= 4:
        return 2, 2
    if count <= 6:
        return 3, 2
    if count <= 9:
        return 3, 3
    return 4, 3


def font_for(size: int):
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def crop_to_tile(image, size: tuple[int, int], focus_x: float, focus_y: float):
    image = ImageOps.exif_transpose(image).convert("RGB")
    source_width, source_height = image.size
    target_width, target_height = size
    scale = max(target_width / source_width, target_height / source_height)
    resized_width = max(target_width, round(source_width * scale))
    resized_height = max(target_height, round(source_height * scale))
    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    left = round((resized_width - target_width) * focus_x)
    top = round((resized_height - target_height) * focus_y)
    left = min(max(0, left), resized_width - target_width)
    top = min(max(0, top), resized_height - target_height)
    crop = resized.crop((left, top, left + target_width, top + target_height))
    source_box = [
        round(left / scale, 3),
        round(top / scale, 3),
        round((left + target_width) / scale, 3),
        round((top + target_height) / scale, 3),
    ]
    return crop, source_box, [source_width, source_height]


def render_board(items: list[dict], output_path: Path) -> dict:
    columns, rows = grid_for(len(items))
    board_width, board_height = BOARD_SIZE
    gap = 24
    margin = 36
    tile_width = (board_width - margin * 2 - gap * (columns - 1)) // columns
    tile_height = (board_height - margin * 2 - gap * (rows - 1)) // rows
    board = Image.new("RGB", BOARD_SIZE, (255, 253, 247))
    draw = ImageDraw.Draw(board)
    font = font_for(max(44, min(tile_width, tile_height) // 8))
    rendered_items = []

    for index, item in enumerate(items):
        row, column = divmod(index, columns)
        x = margin + column * (tile_width + gap)
        y = margin + row * (tile_height + gap)
        path = Path(item["path"]).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"simplified landmark image does not exist: {path}")
        focus_x = float(item.get("focus_x", 0.5))
        focus_y = float(item.get("focus_y", 0.5))
        if not 0.0 <= focus_x <= 1.0 or not 0.0 <= focus_y <= 1.0:
            raise ValueError(f"focus must be within 0..1 for {path}")
        with Image.open(path) as source:
            crop, source_box, source_size = crop_to_tile(source, (tile_width, tile_height), focus_x, focus_y)
        board.paste(crop, (x, y))
        draw.rounded_rectangle((x, y, x + tile_width - 1, y + tile_height - 1), radius=18, outline=(177, 72, 55), width=5)
        badge_size = max(96, min(tile_width, tile_height) // 5)
        badge_box = (x + 18, y + 18, x + 18 + badge_size, y + 18 + badge_size)
        draw.ellipse(badge_box, fill=(255, 255, 255), outline=(198, 40, 40), width=8)
        number = str(item["checkpoint_number"])
        text_box = draw.textbbox((0, 0), number, font=font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        text_x = badge_box[0] + (badge_size - text_width) / 2
        text_y = badge_box[1] + (badge_size - text_height) / 2 - text_box[1]
        draw.text((text_x, text_y), number, font=font, fill=(105, 0, 0))
        rendered_items.append(
            {
                "checkpoint_number": item["checkpoint_number"],
                "checkpoint_name": item["checkpoint_name"],
                "path": str(path),
                "sha256": sha256(path),
                "generation_manifest": item.get("generation_manifest"),
                "focus": [focus_x, focus_y],
                "source_size": source_size,
                "crop_box": source_box,
                "tile_box": [x, y, x + tile_width, y + tile_height],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(output_path, format="PNG", optimize=False, compress_level=9)
    return {
        "path": str(output_path),
        "sha256": sha256(output_path),
        "size": list(BOARD_SIZE),
        "grid": {"columns": columns, "rows": rows},
        "items": rendered_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--mode", choices=("review", "final"), default="final")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    args = parser.parse_args()

    try:
        spec_path = args.spec.expanduser().resolve()
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read landmark board spec: {exc}") from exc
    items = spec.get("items") or []
    if not items:
        raise SystemExit("landmark board spec has no items")
    if args.mode == "final" and len(items) > MAX_ITEMS:
        raise SystemExit("final landmark reference board supports at most 12 items")
    seen_numbers: set[int] = set()
    for item in items:
        number = item.get("checkpoint_number")
        if not isinstance(number, int) or number < 1 or not item.get("checkpoint_name") or not item.get("path"):
            raise SystemExit("each board item requires checkpoint_number, checkpoint_name, and path")
        if number in seen_numbers:
            raise SystemExit(f"duplicate checkpoint number in board spec: {number}")
        seen_numbers.add(number)
        if item.get("approved") is not True:
            raise SystemExit(f"landmark simplification is not approved: checkpoint {number}")
        if args.mode == "final":
            generation_manifest_raw = item.get("generation_manifest")
            if not generation_manifest_raw:
                raise SystemExit(f"final board requires generation_manifest for checkpoint {number}")
            generation_manifest_path = Path(generation_manifest_raw).expanduser().resolve()
            if not generation_manifest_path.is_file():
                raise SystemExit(f"landmark generation manifest does not exist: {generation_manifest_path}")
            try:
                generation = json.loads(generation_manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid landmark generation manifest: {exc}") from exc
            source_path = Path(item["path"]).expanduser().resolve()
            if generation.get("generation_purpose") != "landmark_prepaint":
                raise SystemExit(f"wrong generation purpose for checkpoint {number}")
            if generation.get("provider_authorized") is not True:
                raise SystemExit(f"landmark generation was not authorized for checkpoint {number}")
            if Path(str(generation.get("output_image", ""))).expanduser().resolve() != source_path:
                raise SystemExit(f"landmark generation manifest output mismatch for checkpoint {number}")
            if not source_path.is_file() or generation.get("output_sha256") != sha256(source_path):
                raise SystemExit(f"landmark generation manifest hash mismatch for checkpoint {number}")
            item["generation_manifest"] = str(generation_manifest_path)

    chunks = [items[index : index + MAX_ITEMS] for index in range(0, len(items), MAX_ITEMS)]

    output_base = args.output.expanduser().resolve()
    boards = []
    for index, chunk in enumerate(chunks, start=1):
        output_path = output_base if len(chunks) == 1 else output_base.with_name(f"{output_base.stem}-{index:02d}{output_base.suffix}")
        try:
            boards.append(render_board(chunk, output_path))
        except (OSError, ValueError, KeyError) as exc:
            raise SystemExit(str(exc)) from exc

    sidecar = {
        "schema_version": 1,
        "board_type": "landmark_review_board" if args.mode == "review" else "landmark_reference_board",
        "spec_file": str(spec_path),
        "spec_sha256": sha256(spec_path),
        "boards": boards,
    }
    sidecar_path = args.sidecar.expanduser().resolve()
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    for board in boards:
        print(board["path"])
    print(sidecar_path)


if __name__ == "__main__":
    main()
