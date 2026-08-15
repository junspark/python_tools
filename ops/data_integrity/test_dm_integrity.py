#!/usr/bin/env python3
"""
Unit-style test for dm_integrity core functions using mocked DM API.
Tests: compare(), build_report(), verify_checksums(), save_record(), list_records().
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mock dm module before importing dm_integrity
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

sys.path.insert(0, SCRIPT_DIR)

import dm_integrity as di


def test_compare():
    """Test lightweight file comparison."""
    print("Testing compare()...", end=" ")

    local_files = {
        "file1.dat": {"size": 1000, "mtime": 1234567890},
        "file2.dat": {"size": 2000, "mtime": 1234567891},
        "file3.dat": {"size": 3000, "mtime": 1234567892},
        "local_only.txt": {"size": 500, "mtime": 1234567893},
    }

    catalog_files = {
        "file1.dat": {"size": 1000, "md5": "abc123"},
        "file2.dat": {"size": 2500, "md5": "def456"},
        "file3.dat": {"size": 3000, "md5": "ghi789"},
        "remote_only.txt": {"size": 100, "md5": "jkl012"},
    }

    result = di.compare(local_files, catalog_files)

    assert result["file1.dat"] == "MATCH", "file1 should MATCH"
    assert result["file2.dat"] == "SIZE_MISMATCH", "file2 should have SIZE_MISMATCH"
    assert result["file3.dat"] == "MATCH", "file3 should MATCH"
    assert result["local_only.txt"] == "LOCAL_ONLY", "local_only.txt should be LOCAL_ONLY"
    assert result["remote_only.txt"] == "REMOTE_ONLY", "remote_only.txt should be REMOTE_ONLY"

    print("✓")


def test_build_report():
    """Test report generation."""
    print("Testing build_report()...", end=" ")

    upload_status = {
        "status": "done",
        "n_files": 3,
        "n_completed": 3,
        "n_errors": 0,
        "upload_complete": True,
    }

    comparison = {
        "file1.dat": "MATCH",
        "file2.dat": "MATCH",
        "file3.dat": "MATCH",
    }

    report = di.build_report("test_exp", upload_status, comparison)

    assert report["experiment_name"] == "test_exp"
    assert report["file_stats"]["total"] == 3
    assert report["file_stats"]["good"] == 3
    assert report["file_stats"]["bad"] == 0
    assert report["recommend_deletion"] == True

    comparison_with_mismatch = {
        "file1.dat": "MATCH",
        "file2.dat": "SIZE_MISMATCH",
    }

    report2 = di.build_report("test_exp", upload_status, comparison_with_mismatch)
    assert report2["recommend_deletion"] == False, "Should not recommend deletion if files differ"

    print("✓")


def test_verify_checksums():
    """Test MD5 checksum verification."""
    print("Testing verify_checksums()...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.dat")
        test_content = b"test content for hashing"
        with open(test_file, "wb") as f:
            f.write(test_content)

        actual_md5 = hashlib.md5(test_content).hexdigest()
        wrong_md5 = "0" * 32

        catalog_files = {
            "test.dat": {"size": len(test_content), "md5": actual_md5},
            "wrong_md5.dat": {"size": 100, "md5": wrong_md5},
        }

        result = di.verify_checksums(tmpdir, catalog_files, ["test.dat"])
        assert result["test.dat"] == "CHECKSUM_MATCH", "Should match correct checksum"

        result2 = di.verify_checksums(tmpdir, catalog_files, ["test.dat"])
        assert result2["test.dat"] == "CHECKSUM_MATCH"

    print("✓")


def test_save_and_list_records():
    """Test record save/load."""
    print("Testing save_record() and list_records()...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        report = {
            "experiment_name": "test_exp",
            "timestamp": 1234567890,
            "file_stats": {"good": 10, "bad": 0},
            "recommend_deletion": True,
        }

        filepath = di.save_record(tmpdir, "test_exp", report)
        assert os.path.exists(filepath), "Record file should exist"

        records = di.list_records(tmpdir, "test_exp")
        assert len(records) == 1, "Should have one record"

        with open(records[0][1]) as f:
            loaded = json.load(f)
        assert loaded["experiment_name"] == "test_exp"
        assert loaded["file_stats"]["good"] == 10

    print("✓")


def test_get_upload_status_mock():
    """Test get_upload_status with mocked API."""
    print("Testing get_upload_status (mocked)...", end=" ")

    class MockApi:
        def listUploadRecords(self, queryDict):
            return [{
                "status": "done",
                "nFiles": 100,
                "nCompletedFiles": 100,
                "nProcessingErrors": 0,
            }]

    original_api = di.experimentDaqApi.ExperimentDaqApi
    di.experimentDaqApi.ExperimentDaqApi = MockApi

    try:
        result = di.get_upload_status("test_exp")
        assert result["status"] == "done"
        assert result["upload_complete"] == True
    finally:
        di.experimentDaqApi.ExperimentDaqApi = original_api

    print("✓")


def test_scan_local_files():
    """Test scanning local files."""
    print("Testing scan_local_files()...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "subdir").mkdir()
        Path(tmpdir, "file1.txt").write_text("content1")
        Path(tmpdir, "subdir", "file2.txt").write_text("content2")

        result = di.scan_local_files(tmpdir)

        assert "file1.txt" in result
        assert "subdir/file2.txt" in result or "subdir\\file2.txt" in result
        assert result["file1.txt"]["size"] == len("content1")

    print("✓")


if __name__ == "__main__":
    try:
        test_compare()
        test_build_report()
        test_verify_checksums()
        test_save_and_list_records()
        test_scan_local_files()
        test_get_upload_status_mock()
        print("\nAll tests passed! ✓")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
