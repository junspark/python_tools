#!/usr/bin/env python3
"""Test auto-discovery of recent experiments from DM."""

import sys
import os
from unittest import mock

# Mock epics and dm modules
sys.modules['epics'] = mock.MagicMock()
sys.modules['dm'] = mock.MagicMock()
sys.modules['dm.cat_web_service'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api.datasetCatApi'] = mock.MagicMock()
sys.modules['dm.cat_web_service.api.fileCatApi'] = mock.MagicMock()
sys.modules['dm.daq_web_service'] = mock.MagicMock()
sys.modules['dm.daq_web_service.api'] = mock.MagicMock()
sys.modules['dm.daq_web_service.api.experimentDaqApi'] = mock.MagicMock()
sys.modules['dm.ds_web_service'] = mock.MagicMock()
sys.modules['dm.ds_web_service.api'] = mock.MagicMock()
sys.modules['dm.ds_web_service.api.fileDsApi'] = mock.MagicMock()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import dm_integrity as di


def test_get_recent_experiments():
    """Test getting recent experiments from mocked DM."""
    print("Testing get_recent_experiments()...", end=" ")

    # Mock the ExperimentDaqApi
    mock_records = [
        {"experimentName": "exp_a", "timestamp": 1000},
        {"experimentName": "exp_b", "timestamp": 2000},
        {"experimentName": "exp_c", "timestamp": 1500},
        {"experimentName": "exp_a", "timestamp": 3000},  # Newer exp_a - should use this one
        {"experimentName": "exp_d", "timestamp": 500},
    ]

    mock_api_instance = mock.MagicMock()
    mock_api_instance.listUploadRecords.return_value = mock_records

    mock_api_class = mock.MagicMock(return_value=mock_api_instance)
    mock_api_module = mock.MagicMock()
    mock_api_module.ExperimentDaqApi = mock_api_class

    # Temporarily replace the API module
    original_api = di.experimentDaqApi
    di.experimentDaqApi = mock_api_module

    try:
        recent = di.get_recent_experiments(limit=3)

        # Should return (most recent first): exp_a (3000), exp_b (2000), exp_c (1500),
        # each tagged with its station name (default station is "s1" when no
        # station_configs is passed). Note: exp_a appears twice; we keep the
        # most recent (3000).
        expected = [("exp_a", "s1"), ("exp_b", "s1"), ("exp_c", "s1")]
        assert recent == expected, f"Got {recent}, expected {expected}"
        print(f"✓ Correct experiments in order (most recent first): {recent}")

    finally:
        di.experimentDaqApi = original_api


def test_get_recent_experiments_empty():
    """Test with no experiments."""
    print("Testing get_recent_experiments() with empty list...", end=" ")

    mock_api_instance = mock.MagicMock()
    mock_api_instance.listUploadRecords.return_value = []

    mock_api_class = mock.MagicMock(return_value=mock_api_instance)
    mock_api_module = mock.MagicMock()
    mock_api_module.ExperimentDaqApi = mock_api_class

    original_api = di.experimentDaqApi
    di.experimentDaqApi = mock_api_module

    try:
        recent = di.get_recent_experiments(limit=10)
        assert recent == [], f"Got {recent}, expected []"
        print("✓ Handles empty list correctly")
    finally:
        di.experimentDaqApi = original_api


if __name__ == "__main__":
    try:
        test_get_recent_experiments()
        test_get_recent_experiments_empty()
        print("\n✓ All auto-discovery tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
