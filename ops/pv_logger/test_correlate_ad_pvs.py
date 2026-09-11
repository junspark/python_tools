#!/usr/bin/env python3
"""Hand-rolled tests for correlate_ad_pvs.py - run directly (repo
convention, no pytest runner configured):
    python3 test_correlate_ad_pvs.py
"""

import os
import shutil
import sys
import tempfile
import time

import h5py
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import correlate_ad_pvs as cap
import pv_logger as pl

TMPDIR = None


def setup():
    global TMPDIR
    TMPDIR = tempfile.mkdtemp(prefix="test_correlate_ad_pvs_")


def teardown():
    shutil.rmtree(TMPDIR, ignore_errors=True)


def make_csv(path, base_time, interval, n_rows, numeric_values, nonnumeric_values):
    """A synthetic pv_logger CSV with two PV columns: "numericPV" (all
    parseable floats) and "modePV" (a mix of strings/OFFLINE)."""
    with open(path, "w") as f:
        f.write("Date, numericPV, modePV, \n")
        for i in range(n_rows):
            ts = base_time + i * interval
            f.write(f"{time.ctime(ts)}, {numeric_values[i]}, {nonnumeric_values[i]}\n")


def make_h5(path, frame_timestamps, mtime_override=None):
    with h5py.File(path, "w") as f:
        misc = f.create_group("misc")
        misc.create_dataset("NDArrayTimeStamp", data=np.asarray(frame_timestamps, dtype=float))
        f.create_dataset("exchange/data", data=np.zeros((len(frame_timestamps), 4, 4)))
    if mtime_override is not None:
        os.utime(path, (mtime_override, mtime_override))


def make_h5_no_timestamp(path, n_frames, mtime_override=None):
    with h5py.File(path, "w") as f:
        f.create_dataset("exchange/data", data=np.zeros((n_frames, 4, 4)))
    if mtime_override is not None:
        os.utime(path, (mtime_override, mtime_override))


def test_linear_interpolation_matches_hand_computed():
    base_time = 1_700_000_000.0
    csv_path = os.path.join(TMPDIR, "run1.csv")
    # numericPV rises linearly 0, 10, 20, 30, 40 at t=base, base+5, ...
    make_csv(
        csv_path, base_time, 5.0, 5,
        numeric_values=[0, 10, 20, 30, 40],
        nonnumeric_values=["idle"] * 5,
    )
    query_ts = np.array([base_time + 2.5, base_time + 7.5])
    result = cap.interpolate_pvs(csv_path, ["numericPV"], query_ts)
    assert abs(result["numericPV"][0] - 5.0) < 1e-9, result
    assert abs(result["numericPV"][1] - 15.0) < 1e-9, result
    print("test_linear_interpolation_matches_hand_computed: OK")


def test_linear_interpolation_clamps_at_ends():
    base_time = 1_700_000_000.0
    csv_path = os.path.join(TMPDIR, "run2.csv")
    make_csv(
        csv_path, base_time, 5.0, 3,
        numeric_values=[0, 10, 20],
        nonnumeric_values=["idle"] * 3,
    )
    # Just past either end (10s, within the default 15s gap tolerance for
    # this CSV's 5s logging interval) - clamped to the nearest real value.
    query_ts = np.array([base_time - 10, base_time + 20])
    result = cap.interpolate_pvs(csv_path, ["numericPV"], query_ts)
    assert result["numericPV"][0] == 0.0, result
    assert result["numericPV"][1] == 20.0, result
    print("test_linear_interpolation_clamps_at_ends: OK")


def test_extrapolation_past_gap_tolerance_flagged_offline():
    """A query far past the last (or before the first) logged sample -
    beyond any reasonable gap tolerance - is OFFLINE, not a stale
    constant-extrapolated guess."""
    base_time = 1_700_050_000.0
    csv_path = os.path.join(TMPDIR, "run2b.csv")
    make_csv(
        csv_path, base_time, 5.0, 3,
        numeric_values=[0, 10, 20],
        nonnumeric_values=["idle"] * 3,
    )
    query_ts = np.array([base_time - 100, base_time + 100])
    result = cap.interpolate_pvs(csv_path, ["numericPV"], query_ts)
    assert result["numericPV"][0] == cap.OFFLINE_MARKER, result
    assert result["numericPV"][1] == cap.OFFLINE_MARKER, result
    print("test_extrapolation_past_gap_tolerance_flagged_offline: OK")


def test_nonnumeric_falls_back_to_nearest():
    base_time = 1_700_000_000.0
    csv_path = os.path.join(TMPDIR, "run3.csv")
    make_csv(
        csv_path, base_time, 5.0, 4,
        numeric_values=[0, 10, 20, 30],
        nonnumeric_values=["idle", "OFFLINE", "acquiring", "done"],
    )
    query_ts = np.array([base_time + 0.1, base_time + 9.9, base_time + 15.4])
    result = cap.interpolate_pvs(csv_path, ["modePV"], query_ts)
    assert result["modePV"][0] == "idle", result
    assert result["modePV"][1] == "acquiring", result
    assert result["modePV"][2] == "done", result
    print("test_nonnumeric_falls_back_to_nearest: OK")


def test_offline_gap_flagged_instead_of_interpolated():
    """A frame whose timestamp falls inside a mid-run offline gap gets
    OFFLINE, not a value silently interpolated across the gap."""
    base_time = 1_700_600_000.0
    csv_path = os.path.join(TMPDIR, "run6.csv")
    # numericPV: online at t=0,5 (values 0,10), OFFLINE at t=10,15,20,25,
    # online again at t=30 (value 60) - a 20s gap either side of the hole.
    make_csv(
        csv_path, base_time, 5.0, 7,
        numeric_values=[0, 10, pl.OFFLINE_MARKER, pl.OFFLINE_MARKER, pl.OFFLINE_MARKER, pl.OFFLINE_MARKER, 60],
        nonnumeric_values=["idle"] * 7,
    )
    # Query right in the middle of the gap (t=17.5, ~12.5s from the
    # nearest real sample at t=5) - default threshold (3x the 5s median
    # interval = 15s) should NOT flag this since it's within tolerance...
    near_gap_result = cap.interpolate_pvs(csv_path, ["numericPV"], np.array([base_time + 17.5]))
    assert near_gap_result["numericPV"][0] != cap.OFFLINE_MARKER, near_gap_result
    # ...but an explicit tight threshold should flag the same query.
    result = cap.interpolate_pvs(csv_path, ["numericPV"], np.array([base_time + 17.5]), max_gap_sec=10.0)
    assert result["numericPV"][0] == cap.OFFLINE_MARKER, result
    print("test_offline_gap_flagged_instead_of_interpolated: OK")


def test_offline_after_permanent_drop_flagged():
    """A frame after a PV drops permanently (never comes back online in
    the CSV) gets OFFLINE, not a stale constant-extrapolated value."""
    base_time = 1_700_700_000.0
    csv_path = os.path.join(TMPDIR, "run7.csv")
    make_csv(
        csv_path, base_time, 5.0, 4,
        numeric_values=[0, 10, pl.OFFLINE_MARKER, pl.OFFLINE_MARKER],
        nonnumeric_values=["idle"] * 4,
    )
    # Far past the last real sample (t=5) - well beyond any reasonable
    # inferred threshold.
    result = cap.interpolate_pvs(csv_path, ["numericPV"], np.array([base_time + 100.0]))
    assert result["numericPV"][0] == cap.OFFLINE_MARKER, result
    print("test_offline_after_permanent_drop_flagged: OK")


def test_within_tolerance_still_interpolates():
    """Frames near real samples (within the default gap tolerance) still
    interpolate normally - no regression to the happy path."""
    base_time = 1_700_800_000.0
    csv_path = os.path.join(TMPDIR, "run8.csv")
    make_csv(
        csv_path, base_time, 5.0, 5,
        numeric_values=[0, 10, 20, 30, 40],
        nonnumeric_values=["idle"] * 5,
    )
    query_ts = np.array([base_time + 2.5, base_time + 7.5])
    result = cap.interpolate_pvs(csv_path, ["numericPV"], query_ts)
    assert abs(result["numericPV"][0] - 5.0) < 1e-9, result
    assert abs(result["numericPV"][1] - 15.0) < 1e-9, result
    print("test_within_tolerance_still_interpolates: OK")


def test_get_frame_timestamps_embedded():
    base_time = 1_700_100_000.0
    h5_path = os.path.join(TMPDIR, "scan_0001.h5")
    frame_ts = [base_time, base_time + 1.0, base_time + 2.0]
    make_h5(h5_path, frame_ts, mtime_override=base_time + 2.0)
    timestamps, source = cap.get_frame_timestamps(h5_path)
    assert source == "embedded", source
    assert list(timestamps) == frame_ts, timestamps
    print("test_get_frame_timestamps_embedded: OK")


def test_get_frame_timestamps_mtime_mismatch_still_prefers_embedded():
    base_time = 1_700_200_000.0
    h5_path = os.path.join(TMPDIR, "scan_0002.h5")
    frame_ts = [base_time, base_time + 1.0]
    # mtime is far off (1000s later) - embedded should still win.
    make_h5(h5_path, frame_ts, mtime_override=base_time + 1000.0)
    timestamps, source = cap.get_frame_timestamps(h5_path)
    assert source == "embedded", source
    assert list(timestamps) == frame_ts, timestamps
    print("test_get_frame_timestamps_mtime_mismatch_still_prefers_embedded: OK")


def test_get_frame_timestamps_falls_back_to_mtime():
    mtime = 1_700_300_000.0
    h5_path = os.path.join(TMPDIR, "scan_0003.h5")
    make_h5_no_timestamp(h5_path, n_frames=3, mtime_override=mtime)
    timestamps, source = cap.get_frame_timestamps(h5_path)
    assert source == "mtime", source
    assert len(timestamps) == 3, timestamps
    assert all(abs(t - mtime) < 1e-6 for t in timestamps), timestamps
    print("test_get_frame_timestamps_falls_back_to_mtime: OK")


def test_per_frame_output():
    base_time = 1_700_400_000.0
    csv_path = os.path.join(TMPDIR, "run4.csv")
    make_csv(
        csv_path, base_time, 5.0, 5,
        numeric_values=[0, 10, 20, 30, 40],
        nonnumeric_values=["idle"] * 5,
    )
    h5_path = os.path.join(TMPDIR, "scan_0004.h5")
    frame_ts = [base_time + 2.5, base_time + 7.5]
    make_h5(h5_path, frame_ts, mtime_override=frame_ts[-1])

    timestamps, source = cap.get_frame_timestamps(h5_path)
    pv_values = cap.interpolate_pvs(csv_path, ["numericPV"], timestamps)
    out_path = cap.write_per_frame_csv(h5_path, ["numericPV"], timestamps, pv_values, out_dir=TMPDIR)

    with open(out_path) as f:
        lines = f.read().strip().split("\n")
    assert lines[0] == "frame_index,timestamp,numericPV", lines[0]
    assert len(lines) == 3, lines
    assert lines[1].endswith(",5.0"), lines[1]
    assert lines[2].endswith(",15.0"), lines[2]
    print("test_per_frame_output: OK")


def test_averaged_output():
    base_time = 1_700_500_000.0
    csv_path = os.path.join(TMPDIR, "run5.csv")
    make_csv(
        csv_path, base_time, 5.0, 5,
        numeric_values=[0, 10, 20, 30, 40],
        nonnumeric_values=["idle"] * 5,
    )
    h5_path = os.path.join(TMPDIR, "scan_0005.h5")
    frame_ts = [base_time + 2.5, base_time + 7.5]
    make_h5(h5_path, frame_ts, mtime_override=frame_ts[-1])

    timestamps, source = cap.get_frame_timestamps(h5_path)
    pv_values = cap.interpolate_pvs(csv_path, ["numericPV"], timestamps)
    averaged = {name: cap._average_value(name, values, values[0]) for name, values in pv_values.items()}
    rows = [(os.path.basename(h5_path), float(np.mean(timestamps)), len(timestamps), averaged)]
    out_path = os.path.join(TMPDIR, "combined.csv")
    cap.write_averaged_csv(rows, ["numericPV"], out_path)

    with open(out_path) as f:
        lines = f.read().strip().split("\n")
    assert lines[0] == "filename,mean_timestamp,n_frames,numericPV", lines[0]
    assert len(lines) == 2, lines
    assert lines[1].endswith(",2,10.0"), lines[1]
    print("test_averaged_output: OK")


def test_resolve_pv_names_union_of_pvs_and_groups():
    master_list_path = os.path.join(TMPDIR, "pv_master_list_test.json")
    cfg = {
        "settings": dict(pl._DEFAULT_SETTINGS),
        "pvs": [
            {"name": "hydraZE", "pv": "1id:hydra:ZE", "group": "Eiger Acquisition Settings"},
            {"name": "geXE", "pv": "1id:ge:XE", "group": "Eiger Acquisition Settings"},
            {"name": "furnaceT1", "pv": "1id:furnace:T1", "group": "Furnace"},
        ],
    }
    pl.save_config(cfg, master_list_path)

    names = cap.resolve_pv_names(master_list_path, ["furnaceT1"], ["Eiger Acquisition Settings"])
    assert names == ["furnaceT1", "geXE", "hydraZE"], names
    print("test_resolve_pv_names_union_of_pvs_and_groups: OK")


def test_resolve_pv_names_unknown_group_raises():
    master_list_path = os.path.join(TMPDIR, "pv_master_list_test2.json")
    cfg = {"settings": dict(pl._DEFAULT_SETTINGS), "pvs": [{"name": "a", "pv": "x", "group": "G1"}]}
    pl.save_config(cfg, master_list_path)
    try:
        cap.resolve_pv_names(master_list_path, [], ["NoSuchGroup"])
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("test_resolve_pv_names_unknown_group_raises: OK")


def main():
    setup()
    try:
        test_linear_interpolation_matches_hand_computed()
        test_linear_interpolation_clamps_at_ends()
        test_extrapolation_past_gap_tolerance_flagged_offline()
        test_nonnumeric_falls_back_to_nearest()
        test_offline_gap_flagged_instead_of_interpolated()
        test_offline_after_permanent_drop_flagged()
        test_within_tolerance_still_interpolates()
        test_get_frame_timestamps_embedded()
        test_get_frame_timestamps_mtime_mismatch_still_prefers_embedded()
        test_get_frame_timestamps_falls_back_to_mtime()
        test_per_frame_output()
        test_averaged_output()
        test_resolve_pv_names_union_of_pvs_and_groups()
        test_resolve_pv_names_unknown_group_raises()
    finally:
        teardown()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
