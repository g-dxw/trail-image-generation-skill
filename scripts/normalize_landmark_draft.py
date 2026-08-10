#!/usr/bin/env python3
"""Deterministically normalize one approved landmark draft to a square PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow is required; install it with: python3 -m pip install -r requirements.txt") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--focus-x", type=float, default=0.5)
    parser.add_argument("--focus-y", type=float, default=0.5)
    args = parser.parse_args()

    if not 128 <= args.size <= 2048:
        raise SystemExit("size must be in 128..2048")
    if not 0.0 <= args.focus_x <= 1.0 or not 0.0 <= args.focus_y <= 1.0:
        raise SystemExit("focus values must be in 0..1")
    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"input image does not exist: {source}")

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
        normalized = ImageOps.fit(
            image,
            (args.size, args.size),
            method=Image.Resampling.LANCZOS,
            centering=(args.focus_x, args.focus_y),
        )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(output, format="PNG", optimize=False, compress_level=9)
    print(output)


if __name__ == "__main__":
    main()
