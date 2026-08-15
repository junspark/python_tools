#!/usr/bin/env python3
"""Test device filtering functionality in pv_logger."""

import sys
import os
from unittest import mock

# Mock epics before importing pv_logger
sys.modules['epics'] = mock.MagicMock()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import pv_logger as pl


def test_get_all_devices():
    """Test extracting all unique devices from PV list."""
    print("Testing get_all_devices()...", end=" ")

    cfg = pl.load_config()
    devices = pl.get_all_devices(cfg["pvs"])

    assert len(devices) > 0, "Should find at least one device"
    assert all(isinstance(d, str) for d in devices), "All devices should be strings"
    assert devices == sorted(devices), "Devices should be sorted"

    print(f"✓ Found {len(devices)} devices:")
    for device in devices[:5]:
        print(f"    - {device}")
    if len(devices) > 5:
        print(f"    ... and {len(devices) - 5} more")

    return devices


def test_filter_pvs_by_devices():
    """Test filtering PVs by selected devices."""
    print("\nTesting filter_pvs_by_devices()...", end=" ")

    cfg = pl.load_config()
    all_devices = pl.get_all_devices(cfg["pvs"])

    if not all_devices:
        print("⚠ No devices to test with")
        return

    # Select first device
    selected = [all_devices[0]]
    filtered = pl.filter_pvs_by_devices(cfg["pvs"], selected)

    assert len(filtered) > 0, f"Should find PVs in device '{selected[0]}'"
    assert all(pv["group"] == selected[0] for pv in filtered), "All filtered PVs should be from selected device"

    print(f"✓ Filtered {len(filtered)} PVs from '{selected[0]}'")

    # Test with multiple devices
    if len(all_devices) > 1:
        selected_multi = all_devices[:2]
        filtered_multi = pl.filter_pvs_by_devices(cfg["pvs"], selected_multi)
        assert len(filtered_multi) > 0, "Should find PVs in selected devices"
        print(f"✓ Filtered {len(filtered_multi)} PVs from {len(selected_multi)} devices")

    # Test with empty selection
    filtered_empty = pl.filter_pvs_by_devices(cfg["pvs"], [])
    assert len(filtered_empty) == 0, "Empty selection should return empty list"
    print(f"✓ Empty selection returns empty list")


def test_device_summary():
    """Summary of device distribution."""
    print("\nDevice summary:")

    cfg = pl.load_config()
    devices = pl.get_all_devices(cfg["pvs"])

    for device in devices:
        filtered = pl.filter_pvs_by_devices(cfg["pvs"], [device])
        print(f"  {device:30} {len(filtered):4} PVs")


if __name__ == "__main__":
    try:
        devices = test_get_all_devices()
        test_filter_pvs_by_devices()
        test_device_summary()
        print("\n✓ All device filtering tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
