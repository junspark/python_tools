#!/usr/bin/env python3
from __future__ import annotations
"""Batch dark-correct and export detector images from an S20 experiment folder.

Usage:
    python batch_correct.py <experiment_dir> -o <output_root> [options]

Folder layout expected:
    <experiment_dir>/<detector>/<scan_name>/<files>.h5

Output mirrors input structure:
    <output_root>/<detector>/<scan_name>/<stem>.<combine>.tiff|.npz
"""

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np


def _find_h5_files(experiment_dir: Path, detectors: list[str] | None) -> list[Path]:
    files = []
    for det_dir in sorted(experiment_dir.iterdir()):
        if not det_dir.is_dir():
            continue
        if detectors and det_dir.name not in detectors:
            continue
        for scan_dir in sorted(det_dir.iterdir()):
            if not scan_dir.is_dir():
                continue
            for h5 in sorted(scan_dir.glob("*.h5")):
                files.append(h5)
    return files


def _filter_by_scan(files: list[Path], pattern: str | None) -> list[Path]:
    if not pattern:
        return files
    import fnmatch
    return [f for f in files if fnmatch.fnmatch(f.parent.name, pattern)]


def _write_outputs(image: np.ndarray, stem: str, out_dir: Path, formats: list[str]):
    out_dir.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        if fmt == "tiff":
            try:
                import tifffile
                tifffile.imwrite(out_dir / f"{stem}.tiff", image)
            except ImportError:
                # fallback: PIL
                from PIL import Image
                img_scaled = image  # keep float32; tiff supports it
                Image.fromarray(img_scaled).save(out_dir / f"{stem}.tiff")
        elif fmt == "npz":
            np.savez_compressed(out_dir / f"{stem}.npz", image=image)


def _process_one(args):
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).parents[1]))

    h5_path, out_root, combine, dark_file, white_file, formats = args
    from detector_processing.correction import process_file

    rel = h5_path.relative_to(h5_path.parents[2])  # <detector>/<scan>/<file>
    out_dir = out_root / rel.parent
    stem = h5_path.name.split(".")[0] + f".{combine}"

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            image, meta = process_file(
                h5_path,
                dark_file=dark_file,
                white_file=white_file,
                combine=combine,
            )
        except Exception as exc:
            return str(h5_path), False, str(exc), []

    _write_outputs(image, stem, out_dir, formats)
    warns = [str(x.message) for x in w]
    return str(h5_path), True, None, warns


def main():
    parser = argparse.ArgumentParser(
        description="Batch dark-correct S20 detector HDF5 files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("experiment_dir", type=Path, help="Root experiment folder.")
    parser.add_argument("-o", "--output", type=Path, required=True, dest="output_root",
                        help="Output root directory.")
    parser.add_argument("--detectors", nargs="+", default=None,
                        help="Detector subfolders to process (default: all).")
    parser.add_argument("--scans", default=None,
                        help="Glob pattern to filter scan folder names.")
    parser.add_argument("--combine", choices=["mean", "sum"], default="mean",
                        help="Frame combining method.")
    parser.add_argument("--dark-file", type=Path, default=None,
                        help="Fallback HDF5 file for dark frames.")
    parser.add_argument("--white-file", type=Path, default=None,
                        help="Fallback HDF5 file for white frames.")
    parser.add_argument("--format", nargs="+", choices=["tiff", "npz"],
                        default=["tiff"], dest="formats",
                        help="Output format(s).")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel worker processes.")
    args = parser.parse_args()

    exp_dir = args.experiment_dir.resolve()
    if not exp_dir.is_dir():
        print(f"ERROR: experiment_dir not found: {exp_dir}", file=sys.stderr)
        sys.exit(1)

    files = _find_h5_files(exp_dir, args.detectors)
    files = _filter_by_scan(files, args.scans)

    if not files:
        print("No .h5 files found matching the given filters.")
        sys.exit(0)

    print(f"Found {len(files)} file(s) to process → {args.output_root}")

    tasks = [
        (f, args.output_root, args.combine, args.dark_file, args.white_file, args.formats)
        for f in files
    ]

    n_ok = n_err = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_process_one, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            h5_path, ok, err, warns = fut.result()
            rel = Path(h5_path).relative_to(exp_dir)
            if ok:
                n_ok += 1
                status = "OK"
                if warns:
                    status += f" [{'; '.join(warns)}]"
                print(f"  {rel}  {status}")
            else:
                n_err += 1
                print(f"  {rel}  ERROR: {err}", file=sys.stderr)

    print(f"\nDone: {n_ok} succeeded, {n_err} failed.")
    if n_err:
        sys.exit(1)


if __name__ == "__main__":
    main()
