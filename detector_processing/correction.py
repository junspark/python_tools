from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from .reader import DetectorFile


def dark_correct(
    data: np.ndarray,
    dark: np.ndarray | None,
    white: np.ndarray | None,
) -> np.ndarray:
    """Apply dark-field and flat-field correction to frames.

    Args:
        data:  (N, H, W) float32 raw frames
        dark:  (H, W) float32 averaged dark, or None to skip dark subtraction
        white: (H, W) float32 averaged white, or None to skip flat-field division

    Returns:
        (N, H, W) float32, negatives clamped to 0.
        If both dark and white are provided: (data - dark) / (white - dark)
        If only dark: data - dark
        If neither: data unchanged
    """
    out = data.copy()

    if dark is not None:
        out -= dark[np.newaxis]

    if white is not None:
        denom = white - (dark if dark is not None else 0.0)
        # avoid divide-by-zero: where denom==0, set result to 0
        safe = denom != 0
        out[:, safe] /= denom[safe]
        out[:, ~safe] = 0.0

    np.clip(out, 0, None, out=out)
    return out


def combine_frames(frames: np.ndarray, method: str = "mean") -> np.ndarray:
    """Collapse N frames to a single 2-D image.

    Args:
        frames: (N, H, W) float32
        method: 'mean' or 'sum'

    Returns:
        (H, W) float32
    """
    if method == "sum":
        return frames.sum(axis=0)
    return frames.mean(axis=0)


def process_file(
    path: str | Path,
    *,
    dark_file: str | Path | None = None,
    white_file: str | Path | None = None,
    combine: str = "mean",
) -> tuple[np.ndarray, dict]:
    """Read, dark-correct, and combine frames from one detector HDF5 file.

    Dark/white resolution order:
        1. Embedded exchange/data_dark and exchange/data_white (if non-zero).
        2. dark_file / white_file arguments (read via DetectorFile).
        3. Warn and skip correction if neither is available.

    Args:
        path:       Path to a .h5 detector file.
        dark_file:  Fallback .h5 file containing dark frames.
        white_file: Fallback .h5 file containing white frames.
        combine:    'mean' (default) or 'sum'.

    Returns:
        (image, metadata) — image is (H, W) float32, metadata is a dict.
    """
    with DetectorFile(path) as det:
        data = det.data
        dark = det.dark
        white = det.white
        meta = det.metadata

    # fallbacks
    if dark is None and dark_file is not None:
        with DetectorFile(dark_file) as d:
            dark = d.dark
        if dark is None:
            warnings.warn(f"dark_file {dark_file} has all-zero dark frames; skipping dark subtraction")

    if white is None and white_file is not None:
        with DetectorFile(white_file) as d:
            white = d.white
        if white is None:
            warnings.warn(f"white_file {white_file} has all-zero white frames; skipping flat-field")

    if dark is None and white is None:
        warnings.warn(f"{path}: no dark or white available; returning raw combined frames")

    corrected = dark_correct(data, dark, white)
    image = combine_frames(corrected, method=combine)
    meta["combine"] = combine
    return image, meta
