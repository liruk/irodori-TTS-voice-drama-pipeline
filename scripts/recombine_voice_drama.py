#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from generate_voice_drama import append_wave_files, sanitize_filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recombine an existing voice drama after manual clip replacement.")
    parser.add_argument("manifest_csv", type=Path)
    parser.add_argument("--output-wav", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_csv = args.manifest_csv
    if not manifest_csv.exists():
        raise SystemExit(f"Manifest not found: {manifest_csv}")

    with manifest_csv.open(encoding="utf-8-sig", newline="") as fp:
        rows = list(csv.DictReader(fp))
    if not rows:
        raise SystemExit("Manifest CSV is empty.")

    for row in rows:
        output_path = Path(row["output_path"])
        if not output_path.exists():
            raise SystemExit(f"Missing segment file: {output_path}")

    if args.output_wav:
        output_wav = args.output_wav
    else:
        manifest_dir = manifest_csv.parent
        title = manifest_dir.name
        output_wav = manifest_dir / f"{sanitize_filename(title, max_len=100)}__recombined.wav"

    append_wave_files(rows, output_wav)
    print(output_wav.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
