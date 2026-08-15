from __future__ import annotations

import warnings
from pathlib import Path

import h5py
import numpy as np


def _detect_detector(path: Path, h5file: h5py.File) -> str:
    suffix = "".join(path.suffixes).lower()
    if suffix == ".vrx.h5":
        return "varexE"
    if suffix == ".pmg.h5":
        return "pimega"
    if "DetModel" in h5file:
        raw = h5file["DetModel"][()]
        if isinstance(raw, (np.ndarray, list)):
            raw = raw.flat[0]
        if isinstance(raw, bytes):
            raw = raw.decode()
        return str(raw)
    return "unknown"


def _valid_frames(ds: h5py.Dataset) -> np.ndarray | None:
    """Return dataset as array if it exists and has non-zero pixels, else None."""
    arr = ds[()].astype(np.float32)
    if arr.max() == 0:
        return None
    return arr


class DetectorFile:
    """Read a single HDF5 detector file from the S20 experiment layout.

    All detectors share the same internal structure:
        exchange/data        – raw frames  (N, H, W) uint16
        exchange/data_dark   – dark frames (M, H, W) uint16
        exchange/data_white  – white frames (K, H, W) uint16

    Use as a context manager or call .close() when done.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._h5 = h5py.File(self._path, "r")
        self._detector = _detect_detector(self._path, self._h5)

    # --- context manager ---

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self._h5.close()

    # --- properties ---

    @property
    def detector(self) -> str:
        return self._detector

    @property
    def path(self) -> Path:
        return self._path

    @property
    def data(self) -> np.ndarray:
        """Raw frames as float32 (N, H, W)."""
        return self._h5["exchange"]["data"][()].astype(np.float32)

    @property
    def dark(self) -> np.ndarray | None:
        """Dark frames averaged to (H, W) float32, or None if absent/all-zero."""
        ds = self._h5["exchange"].get("data_dark")
        if ds is None:
            return None
        arr = _valid_frames(ds)
        if arr is None:
            return None
        return arr.mean(axis=0)

    @property
    def white(self) -> np.ndarray | None:
        """White frames averaged to (H, W) float32, or None if absent/all-zero."""
        ds = self._h5["exchange"].get("data_white")
        if ds is None:
            return None
        arr = _valid_frames(ds)
        if arr is None:
            return None
        return arr.mean(axis=0)

    @property
    def metadata(self) -> dict:
        h = self._h5
        meta = {
            "detector": self._detector,
            "path": str(self._path),
            "scan": self._path.stem,
        }
        # detector geometry
        for key in ("DetMaxSizeX", "DetMaxSizeY", "DetModel"):
            if key in h:
                v = h[key][()]
                if hasattr(v, "flat"):
                    v = v.flat[0]
                if isinstance(v, bytes):
                    v = v.decode()
                meta[key] = v
        # sample name from misc
        if "misc" in h and "DetSampleName" in h["misc"]:
            raw = h["misc"]["DetSampleName"][()]
            if hasattr(raw, "flat"):
                raw = raw.flat[0]
            if isinstance(raw, bytes):
                raw = raw.decode()
            meta["sample"] = raw
        return meta
