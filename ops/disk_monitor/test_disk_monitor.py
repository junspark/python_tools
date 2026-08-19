#!/usr/bin/env python3
"""
Unit test for disk_monitor.top_level_breakdown() (shells out to the real
`du` binary against a throwaway temp directory - no mocking, since the
whole point is du's own output format).
"""

import os
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import disk_monitor as dm


def test_top_level_breakdown():
    print("Testing top_level_breakdown()...", end=" ")

    with tempfile.TemporaryDirectory() as td:
        # Three subdirectories of clearly different sizes, plus a loose
        # file directly in td (which du folds into td's own total line -
        # must not show up as a "top-level folder" itself).
        sizes = {"biggest": 300_000, "middle": 30_000, "smallest": 3_000}
        for name, size in sizes.items():
            sub = os.path.join(td, name)
            os.makedirs(sub)
            with open(os.path.join(sub, "data.bin"), "wb") as f:
                f.write(b"\0" * size)
        with open(os.path.join(td, "loose_file.bin"), "wb") as f:
            f.write(b"\0" * 1_000_000)

        entries = dm.top_level_breakdown(td, top_n=5)

        names = [e["name"] for e in entries]
        assert names == ["biggest", "middle", "smallest"], names
        assert os.path.join(td, "loose_file.bin") not in [e["path"] for e in entries]
        assert td not in [e["path"] for e in entries]

        for e in entries:
            assert e["size_bytes"] > 0
            assert e["mtime"] is None or isinstance(e["mtime"], float)

        # top_n actually caps the result.
        capped = dm.top_level_breakdown(td, top_n=2)
        assert [e["name"] for e in capped] == ["biggest", "middle"]

    print("✓")


def test_top_level_breakdown_bad_path():
    print("Testing top_level_breakdown() on a nonexistent path...", end=" ")

    try:
        dm.top_level_breakdown("/no/such/path/xyz123")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass

    print("✓")


def test_spawn_du_cancellable():
    """The GUI needs to be able to kill a scan mid-flight (see
    disk_monitor_gui.py's _TopFoldersWorker.cancel) - exercise that same
    spawn-then-kill sequence directly against a real, large-ish temp
    directory, confirming the process actually dies and communicate()
    returns instead of hanging."""
    print("Testing spawn_du() can be killed before it finishes...", end=" ")

    with tempfile.TemporaryDirectory() as td:
        sub = os.path.join(td, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "data.bin"), "wb") as f:
            f.write(b"\0" * 10_000)

        proc = dm.spawn_du(td)
        proc.kill()
        stdout, stderr = proc.communicate(timeout=10)
        assert proc.returncode != 0

    print("✓")


if __name__ == "__main__":
    try:
        test_top_level_breakdown()
        test_top_level_breakdown_bad_path()
        test_spawn_du_cancellable()
        print("\nAll tests passed! ✓")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
