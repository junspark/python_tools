#!/usr/bin/env python3
"""
Correlate a pv_logger CSV against area-detector HDF5 files - for each
detector frame, interpolate the requested PVs' values at that frame's
acquisition time.

Area-detector acquisition and PV logging are asynchronous (pv_logger.py
samples every settings.log_interval_sec, independent of when a detector
actually fires), so a frame's timestamp almost never lines up exactly
with a logged row. This tool bridges that gap: given a group of HDF5
files and a list of PVs (by name and/or pv_master_list group), it
resolves each frame's timestamp - preferring the per-frame timestamp
embedded by the areaDetector HDF5 plugin (NDFileHDF5) over file mtime,
since mtime only reflects when the file was closed, not when each frame
in it was collected - and interpolates every requested PV to that time
(linear for numeric PVs, nearest-sample for non-numeric/OFFLINE ones).
If a PV was actually offline at a frame's time - the nearest real sample
is more than --max-gap-sec away, whether inside a mid-run outage or past
a permanent drop - that frame gets "OFFLINE" instead of a numeric guess,
rather than silently interpolating/extrapolating across the gap.

Subcommands
-----------
per-frame  One CSV per input HDF5 file (<file>_pvs.csv, or under
           --out-dir), one row per frame - for per-shot metadata.
averaged   One combined CSV for the whole input series, one row per
           file with its frames' PV values averaged - for a per-scan
           summary.

The exact HDF5 dataset path for per-frame timestamps depends on how this
beamline's NDFileHDF5 layout.xml is configured - no such file exists in
this repo to read a default from, so the lookup tries a couple of
plausible ADCore-standard paths and lets --timestamp-attr override it.
If nothing is found, every frame in that file falls back to mtime and a
warning is printed - run with --inspect on one real file first to find
the right path if this happens.

Usage examples
--------------
  python correlate_ad_pvs.py inspect --file scan_0001.h5
  python correlate_ad_pvs.py per-frame --csv run1.csv --files 'scan_*.h5' \
      --pvs hydraZE geXE --groups "Eiger Acquisition Settings" \
      --pv-master-list pv_master_list_s1.json
  python correlate_ad_pvs.py averaged --csv run1.csv --files 'scan_*.h5' \
      --pvs hydraZE geXE --out combined_pvs.csv \
      --pv-master-list pv_master_list_s1.json
"""

import argparse
import csv
import glob
import os
import sys
import time

import h5py
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import pv_logger as pl

OFFLINE_MARKER = pl.OFFLINE_MARKER

# ADCore's NDFileHDF5 plugin can be configured (via layout.xml) to embed
# any NDAttribute as a per-frame dataset - the exact group path depends
# on that layout.xml, which isn't present anywhere in this repo. The
# first two candidates match what the sibling mpe_wf_saxs_waxs repo
# documents as the actual on-disk convention at APS 20-ID/1-ID
# (confirmed there via h5py inspection of real detector files); the
# rest are generic ADCore/NeXus example-layout paths kept as a
# further-fallback guess. Tried in order; first one present wins.
# Overridable via --timestamp-attr since a given beamline's layout.xml
# may use something else entirely.
DEFAULT_TIMESTAMP_ATTR_CANDIDATES = [
    "misc/NDArrayTimeStamp",
    "misc/NDArrayEpicsTSSec",
    "/entry/instrument/NDAttributes/NDArrayTimeStamp",
    "/entry/instrument/NDAttributes/NDArrayEpicsTSSec",
    "/entry/instrument/NDAttributes/timeStamp",
]
# Main image stack, one frame per entry along the first axis - used only
# to get a frame count when no timestamp attribute is found at all.
# "exchange/data" matches the confirmed on-disk layout at APS 20-ID/1-ID
# (mpe_wf_saxs_waxs); "/entry/data/data" is the generic ADCore/NeXus
# fallback guess.
DEFAULT_DATASET_PATH = "exchange/data"

# If the embedded per-frame timestamp's mean disagrees with the file's
# mtime by more than this many seconds, warn - still prefer the embedded
# value regardless (per direct confirmation: frame-by-frame is more
# trustworthy than a single whole-file mtime).
MTIME_DISCREPANCY_WARN_SEC = 30.0

# Default "how far is too far" gap threshold for numeric PVs, as a
# multiple of the CSV's own median logging interval, when --max-gap-sec
# isn't given: a single missed sample (interval ~= 1x) shouldn't flag,
# but a PV that's actually offline (interval ~= several x, or a
# permanent drop) should - per direct confirmation, a frame whose
# nearest real sample is this far away gets OFFLINE instead of a
# numeric guess, rather than silently interpolating across the gap or
# extrapolating past a permanent drop.
DEFAULT_MAX_GAP_MULTIPLIER = 3.0


# ---------------------------------------------------------------------------
# HDF5 frame timestamps
# ---------------------------------------------------------------------------

def _find_timestamp_dataset(h5file, timestamp_attr=None):
    """Return the first matching per-frame timestamp dataset's path, or
    None if none of the candidates exist in this file."""
    candidates = [timestamp_attr] if timestamp_attr else DEFAULT_TIMESTAMP_ATTR_CANDIDATES
    for path in candidates:
        if path in h5file:
            return path
    return None


def list_nd_attributes(h5_path):
    """Every dataset path under this file's "misc" group (the confirmed
    per-frame-NDAttribute location at APS 20-ID/1-ID) and, in case a
    different beamline/layout.xml is in play, under the generic ADCore
    example-layout group /entry/instrument/NDAttributes too - printed by
    the `inspect` subcommand so a user can find the real per-frame
    timestamp attribute path for --timestamp-attr when none of
    DEFAULT_TIMESTAMP_ATTR_CANDIDATES match."""
    found = []
    with h5py.File(h5_path, "r") as f:
        for group_path in ("misc", "/entry/instrument/NDAttributes"):
            group = f.get(group_path)
            if group is None:
                continue
            group.visit(lambda name, prefix=group_path: found.append(f"{prefix}/{name}"))
    return found


def get_frame_timestamps(h5_path, timestamp_attr=None, dataset_path=DEFAULT_DATASET_PATH):
    """Resolve one timestamp per frame in h5_path.

    Prefers the embedded per-frame NDAttribute timestamp dataset (see
    _find_timestamp_dataset) over file mtime, cross-checking the two -
    mtime only marks when the file was closed, not when each frame in it
    was actually collected, so on any disagreement the embedded value
    wins (a warning is printed, the file is not rejected).

    Falls back to mtime, repeated for every frame, if no embedded
    timestamp dataset is found at all - frame count in that case comes
    from dataset_path's first axis (defaulting to 1 if that's also
    missing, e.g. a malformed file).

    Returns (timestamps: np.ndarray of float epoch seconds, source: str
    - "embedded" or "mtime", one entry per frame).
    """
    mtime = os.path.getmtime(h5_path)

    with h5py.File(h5_path, "r") as f:
        ts_path = _find_timestamp_dataset(f, timestamp_attr)
        if ts_path is not None:
            timestamps = np.asarray(f[ts_path][()], dtype=float).reshape(-1)
            mean_ts = float(np.mean(timestamps))
            if abs(mean_ts - mtime) > MTIME_DISCREPANCY_WARN_SEC:
                print(
                    f"warning: {h5_path}: embedded timestamp mean "
                    f"({time.ctime(mean_ts)}) differs from file mtime "
                    f"({time.ctime(mtime)}) by {abs(mean_ts - mtime):.1f}s - "
                    "using embedded per-frame timestamps anyway.",
                    file=sys.stderr,
                )
            return timestamps, "embedded"

        if dataset_path in f:
            n_frames = f[dataset_path].shape[0]
        else:
            n_frames = 1
        print(
            f"warning: {h5_path}: no per-frame timestamp dataset found "
            f"(tried {timestamp_attr or DEFAULT_TIMESTAMP_ATTR_CANDIDATES}) - "
            f"falling back to file mtime for all {n_frames} frame(s). Run "
            "`correlate_ad_pvs.py inspect --file ...` on this file and pass "
            "--timestamp-attr to fix this.",
            file=sys.stderr,
        )
        return np.full(n_frames, mtime, dtype=float), "mtime"


# ---------------------------------------------------------------------------
# PV logger CSV interpolation
# ---------------------------------------------------------------------------

def _parse_csv_timestamp(date_str):
    """Inverse of pv_logger.write_row's time.ctime(timestamp) - same
    local-timezone assumption, so this only round-trips correctly when
    run on the same host (or a host in the same timezone) as the logger."""
    return time.mktime(time.strptime(date_str, "%a %b %d %H:%M:%S %Y"))


def load_pv_logger_csv(csv_path):
    """Read a pv_logger CSV back into (timestamps: np.ndarray, columns:
    {pv_name: [raw_str, ...]}) - raw strings kept as-is (including
    "OFFLINE") so callers can decide per-PV whether to treat it as
    numeric or not, same shape pv_logger.read_logged_pv_names() expects
    for the header."""
    names = pl.read_logged_pv_names(csv_path)
    timestamps = []
    columns = {name: [] for name in names}
    with open(csv_path) as f:
        reader = csv.reader(f, skipinitialspace=True)
        header_seen = False
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if not header_seen:
                header_seen = True
                continue
            if not row[0].strip():
                continue
            timestamps.append(_parse_csv_timestamp(row[0]))
            for name, value in zip(names, row[1:]):
                columns[name].append(value)
    return np.asarray(timestamps, dtype=float), columns


def _is_numeric_column(raw_values):
    seen_value = False
    for v in raw_values:
        if v == OFFLINE_MARKER:
            continue
        seen_value = True
        try:
            float(v)
        except ValueError:
            return False
    return seen_value


def _infer_max_gap_sec(logged_ts):
    """Default gap threshold when max_gap_sec isn't given explicitly: a
    multiple of the CSV's own median logging interval (see
    DEFAULT_MAX_GAP_MULTIPLIER). Returns inf (never flag) if there are
    fewer than two logged rows to infer an interval from."""
    if len(logged_ts) < 2:
        return float("inf")
    intervals = np.diff(np.sort(logged_ts))
    return DEFAULT_MAX_GAP_MULTIPLIER * float(np.median(intervals))


def interpolate_pvs(csv_path, pv_names, query_timestamps, max_gap_sec=None):
    """For each name in pv_names, resolve its value at every timestamp in
    query_timestamps against csv_path's logged rows.

    Numeric PVs (every non-OFFLINE cell parses as a float): linear
    interpolation (np.interp) against the logged timestamps that do have
    a numeric value for this PV, clamped at the ends - *unless* the
    nearest real (non-OFFLINE) logged sample is more than max_gap_sec
    away from the query timestamp, in which case the result is the
    literal string "OFFLINE" instead of a numeric guess. This covers a
    frame whose timestamp falls inside a mid-run offline gap (would
    otherwise be silently bridged by interpolation) and a frame after a
    permanent drop (would otherwise be silently constant-extrapolated
    forever). max_gap_sec defaults to _infer_max_gap_sec(logged_ts) - a
    multiple of the CSV's own median logging interval - when None.

    Non-numeric PVs (any string value, or all-OFFLINE): nearest-in-time
    logged value instead - interpolating a string doesn't mean anything,
    and a state/mode PV is piecewise-constant between samples anyway.
    An all-OFFLINE column already yields OFFLINE for every frame this
    way, with no separate gap check needed.

    Returns {pv_name: [value, ...]} aligned with query_timestamps, values
    as float for numeric PVs (or the string "OFFLINE" past a gap) or str
    for non-numeric ones. Raises ValueError for a name not present in
    the CSV header.
    """
    logged_ts, columns = load_pv_logger_csv(csv_path)
    if len(logged_ts) == 0:
        raise ValueError(f"{csv_path}: no logged rows to interpolate against")
    gap_threshold = max_gap_sec if max_gap_sec is not None else _infer_max_gap_sec(logged_ts)

    results = {}
    for name in pv_names:
        if name not in columns:
            raise ValueError(f"{csv_path}: PV '{name}' not found in logged columns")
        raw_values = columns[name]
        if _is_numeric_column(raw_values):
            valid = [i for i, v in enumerate(raw_values) if v != OFFLINE_MARKER]
            valid_ts = logged_ts[valid]
            valid_vals = np.asarray([float(raw_values[i]) for i in valid], dtype=float)
            order = np.argsort(valid_ts)
            valid_ts = valid_ts[order]
            valid_vals = valid_vals[order]
            interpolated = np.interp(query_timestamps, valid_ts, valid_vals)
            nearest_gap = np.min(np.abs(valid_ts[None, :] - np.asarray(query_timestamps)[:, None]), axis=1)
            results[name] = [
                OFFLINE_MARKER if gap > gap_threshold else float(val)
                for val, gap in zip(interpolated, nearest_gap)
            ]
        else:
            results[name] = [
                raw_values[int(np.argmin(np.abs(logged_ts - qt)))]
                for qt in query_timestamps
            ]
    return results


# ---------------------------------------------------------------------------
# PV / group resolution
# ---------------------------------------------------------------------------

def resolve_pv_names(pv_master_list_path, requested_names, requested_groups):
    """Union of explicit PV names and every PV in each requested group,
    resolved against pv_master_list_path's "pvs" entries - reuses
    pv_logger.get_all_devices/filter_pvs_by_devices (the same group
    concept the GUI's device-selection dialog filters on) rather than
    re-implementing group lookup here."""
    names = set(requested_names or [])
    if requested_groups:
        cfg = pl.load_config(pv_master_list_path)
        all_devices = pl.get_all_devices(cfg["pvs"])
        unknown = set(requested_groups) - set(all_devices)
        if unknown:
            raise ValueError(f"Unknown group(s): {sorted(unknown)}")
        for entry in pl.filter_pvs_by_devices(cfg["pvs"], requested_groups):
            names.add(entry["name"])
    if not names:
        raise ValueError("No PVs requested - pass --pvs and/or --groups")
    return sorted(names)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _expand_files(patterns):
    files = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        files.extend(matches if matches else [pattern])
    seen = set()
    unique_files = []
    for path in files:
        if path not in seen:
            seen.add(path)
            unique_files.append(path)
    return unique_files


def write_per_frame_csv(h5_path, pv_names, timestamps, pv_values, out_dir=None):
    stem = os.path.splitext(os.path.basename(h5_path))[0]
    out_path = os.path.join(out_dir or os.path.dirname(h5_path) or ".", f"{stem}_pvs.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_index", "timestamp"] + pv_names)
        for i, ts in enumerate(timestamps):
            writer.writerow([i, time.ctime(ts)] + [pv_values[name][i] for name in pv_names])
    return out_path


def _average_value(name, values, raw_first):
    """Mean of whatever numeric (non-OFFLINE) values are present, or
    raw_first (values[0]) if none are - i.e. a numeric PV averages over
    its online frames only, and a PV that's OFFLINE for every frame in
    this file stays "OFFLINE" rather than crashing np.mean on a string."""
    numeric = [v for v in values if isinstance(v, float)]
    if numeric:
        return float(np.mean(numeric))
    return raw_first


def write_averaged_csv(rows, pv_names, out_path):
    """rows: [(filename, mean_timestamp, n_frames, {pv_name: averaged_value}), ...]"""
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "mean_timestamp", "n_frames"] + pv_names)
        for filename, mean_ts, n_frames, averaged in rows:
            writer.writerow([filename, time.ctime(mean_ts), n_frames] + [averaged[name] for name in pv_names])


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_inspect(args):
    attrs = list_nd_attributes(args.file)
    if not attrs:
        print(f"No /entry/instrument/NDAttributes group found in {args.file} "
              "- this file may not have any embedded NDAttributes, or uses a "
              "different HDF5 layout. Falling back to mtime is your only option.")
        return
    print(f"NDAttribute datasets found in {args.file}:")
    for path in attrs:
        print(f"  {path}")
    print("\nPass the per-frame timestamp one of these via --timestamp-attr.")


def cmd_per_frame(args):
    pv_names = resolve_pv_names(args.pv_master_list, args.pvs, args.groups)
    files = _expand_files(args.files)
    for h5_path in files:
        timestamps, source = get_frame_timestamps(h5_path, args.timestamp_attr, args.dataset_path)
        pv_values = interpolate_pvs(args.csv, pv_names, timestamps, args.max_gap_sec)
        out_path = write_per_frame_csv(h5_path, pv_names, timestamps, pv_values, args.out_dir)
        print(f"{h5_path}: {len(timestamps)} frame(s), timestamps from {source} -> {out_path}")


def cmd_averaged(args):
    pv_names = resolve_pv_names(args.pv_master_list, args.pvs, args.groups)
    files = _expand_files(args.files)
    rows = []
    for h5_path in files:
        timestamps, source = get_frame_timestamps(h5_path, args.timestamp_attr, args.dataset_path)
        pv_values = interpolate_pvs(args.csv, pv_names, timestamps, args.max_gap_sec)
        averaged = {
            name: _average_value(name, values, values[0])
            for name, values in pv_values.items()
        }
        rows.append((os.path.basename(h5_path), float(np.mean(timestamps)), len(timestamps), averaged))
        print(f"{h5_path}: {len(timestamps)} frame(s), timestamps from {source}")
    write_averaged_csv(rows, pv_names, args.out)
    print(f"Wrote {len(rows)} row(s) -> {args.out}")


def _add_common_args(sub):
    sub.add_argument("--csv", required=True, help="pv_logger-produced CSV to interpolate against")
    sub.add_argument("--files", nargs="+", required=True, help="Area-detector HDF5 file(s) or glob pattern(s)")
    sub.add_argument("--pvs", nargs="*", default=[], help="PV names (CSV column headers) to extract")
    sub.add_argument("--groups", nargs="*", default=[], help="pv_master_list group name(s) to extract, e.g. 'Eiger Acquisition Settings'")
    sub.add_argument("--pv-master-list", help="Required if --groups is used - the pv_master_list_*.json to resolve group names against")
    sub.add_argument("--timestamp-attr", default=None, help="HDF5 dataset path for the per-frame timestamp (see `inspect`); default tries a few common ADCore paths")
    sub.add_argument("--dataset-path", default=DEFAULT_DATASET_PATH, help=f"HDF5 dataset path for the main image stack, used for frame count when no timestamp attribute is found (default: {DEFAULT_DATASET_PATH})")
    sub.add_argument("--max-gap-sec", type=float, default=None,
                      help="For a numeric PV, if the nearest real (online) logged sample is more than this many "
                           "seconds from a frame's timestamp, write OFFLINE for that PV/frame instead of an "
                           f"interpolated/extrapolated guess (default: {DEFAULT_MAX_GAP_MULTIPLIER}x the CSV's own median logging interval)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="List embedded NDAttribute datasets in one HDF5 file")
    p_inspect.add_argument("--file", required=True)
    p_inspect.set_defaults(func=cmd_inspect)

    p_per_frame = sub.add_parser("per-frame", help="One PV-metadata CSV per input file, one row per frame")
    _add_common_args(p_per_frame)
    p_per_frame.add_argument("--out-dir", default=None, help="Directory for output CSVs (default: next to each input file)")
    p_per_frame.set_defaults(func=cmd_per_frame)

    p_averaged = sub.add_parser("averaged", help="One combined CSV for the whole file series, one row per file (frame-averaged)")
    _add_common_args(p_averaged)
    p_averaged.add_argument("--out", required=True, help="Path for the combined output CSV")
    p_averaged.set_defaults(func=cmd_averaged)

    args = parser.parse_args()
    if getattr(args, "groups", None) and not args.pv_master_list:
        parser.error("--pv-master-list is required when --groups is used")
    args.func(args)


if __name__ == "__main__":
    main()
