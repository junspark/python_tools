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
import checksum_worker


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


def test_find_relocated_files():
    """A file present on both sides but under a different relative path
    should be paired by basename+size, not left as two unrelated LOCAL_
    ONLY/REMOTE_ONLY entries. Zero-byte files and files with no basename
    match on the other side must not be paired."""
    print("Testing find_relocated_files()...", end=" ")

    local_files = {
        "raw/scan_0042.h5": {"size": 5000, "mtime": 1},
        "raw/empty.dat": {"size": 0, "mtime": 1},
        "raw/never_uploaded.dat": {"size": 999, "mtime": 1},
    }
    catalog_files = {
        "archive/2026/scan_0042.h5": {"size": 5000, "md5": "abc"},
        "archive/2026/empty.dat": {"size": 0, "md5": "def"},
        "archive/2026/deleted_locally.dat": {"size": 777, "md5": "ghi"},
    }
    comparison = di.compare(local_files, catalog_files)
    assert comparison["raw/scan_0042.h5"] == "LOCAL_ONLY"
    assert comparison["archive/2026/scan_0042.h5"] == "REMOTE_ONLY"

    relocated = di.find_relocated_files(local_files, catalog_files, comparison)

    assert len(relocated) == 1, f"expected exactly one relocated pair (empty.dat must be skipped), got {relocated}"
    pair = relocated[0]
    assert pair["local_path"] == "raw/scan_0042.h5"
    assert pair["remote_path"] == "archive/2026/scan_0042.h5"
    assert pair["size"] == 5000

    # Genuinely un-paired files (different basenames, or a same-basename
    # zero-byte file) must not show up as relocated.
    relocated_paths = {pair["local_path"] for pair in relocated} | {pair["remote_path"] for pair in relocated}
    assert "raw/never_uploaded.dat" not in relocated_paths
    assert "archive/2026/deleted_locally.dat" not in relocated_paths
    assert "raw/empty.dat" not in relocated_paths
    assert "archive/2026/empty.dat" not in relocated_paths

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

    # A relocated pair must be subtracted out of local_only/remote_only
    # (not double-counted as two separate "missing" problems) and must
    # count toward neither good nor bad - but must still block
    # recommend_deletion, since a basename+size match is never checksum-
    # confirmed (verify_checksums only ever hashes MATCH-status paths).
    comparison_with_relocation = {
        "file1.dat": "MATCH",
        "raw/moved.h5": "LOCAL_ONLY",
        "archive/moved.h5": "REMOTE_ONLY",
    }
    relocated_files = [{"local_path": "raw/moved.h5", "remote_path": "archive/moved.h5", "size": 123}]
    report3 = di.build_report("test_exp", upload_status, comparison_with_relocation, relocated_files=relocated_files)

    stats = report3["file_stats"]
    assert stats["relocated"] == 1
    assert stats["local_only"] == 0, "the relocated pair's LOCAL_ONLY path must not also count as local_only"
    assert stats["remote_only"] == 0, "the relocated pair's REMOTE_ONLY path must not also count as remote_only"
    assert stats["good"] == 1 and stats["bad"] == 0, "relocated files count toward neither good nor bad"
    assert stats["total"] == 3, "total is still every raw comparison path, relocated or not"
    assert report3["relocated_files"] == relocated_files
    assert report3["recommend_deletion"] == False, \
        "a basename+size-only match must never authorize deletion on its own"

    print("✓")


def test_checksum_worker_passes_through_relocated_files():
    """checksum_worker.py's run() reads job_spec["relocated_files"] and
    forwards it into build_report() - and must default safely to []
    for a job spec from an older _ChecksumLaunchWorker that predates this
    key, rather than KeyError-ing a running job mid-upgrade."""
    print("Testing checksum_worker.run() forwards relocated_files...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        records_dir = os.path.join(tmpdir, "records")
        job_spec_path = os.path.join(tmpdir, "job.jobspec")
        status_file = os.path.join(tmpdir, "status.json")

        job_spec = {
            "experiment_name": "test_exp",
            "beamline": "s1",
            "local_root": tmpdir,
            "upload_status": {"upload_complete": True},
            "catalog_files": {},
            "comparison": {
                "good.h5": "MATCH",
                "raw/moved.h5": "LOCAL_ONLY",
                "archive/moved.h5": "REMOTE_ONLY",
            },
            "paths_to_verify": [],
            "relocated_files": [{"local_path": "raw/moved.h5", "remote_path": "archive/moved.h5", "size": 123}],
            "records_dir": records_dir,
        }
        with open(job_spec_path, "w") as f:
            json.dump(job_spec, f)

        rc = checksum_worker.run(job_spec_path, status_file)
        assert rc == 0

        with open(status_file) as f:
            status = json.load(f)
        assert status["state"] == "DONE"
        with open(status["report_path"]) as f:
            report = json.load(f)
        assert report["file_stats"]["relocated"] == 1
        assert report["relocated_files"] == job_spec["relocated_files"]

        # A job spec from before relocated_files existed must not crash -
        # spec.get(..., []) should quietly default to no relocations.
        del job_spec["relocated_files"]
        status_file2 = os.path.join(tmpdir, "status2.json")
        job_spec_path2 = os.path.join(tmpdir, "job2.jobspec")
        with open(job_spec_path2, "w") as f:
            json.dump(job_spec, f)
        rc2 = checksum_worker.run(job_spec_path2, status_file2)
        assert rc2 == 0
        with open(status_file2) as f:
            status2 = json.load(f)
        with open(status2["report_path"]) as f:
            report2 = json.load(f)
        assert report2["file_stats"]["relocated"] == 0

    print("✓")


def test_diff_directories():
    """A whole subdirectory with zero presence in the catalog should be
    named directly, not just implied by its files' individual LOCAL_ONLY
    statuses."""
    print("Testing diff_directories()...", end=" ")

    comparison = {
        "top.dat": "MATCH",
        "landed/a.dat": "MATCH",
        "landed/sub/b.dat": "MATCH",
        "never_uploaded/c.dat": "LOCAL_ONLY",
        "never_uploaded/d.dat": "LOCAL_ONLY",
        "cleaned_up/e.dat": "REMOTE_ONLY",
    }

    missing_dirs, extra_dirs = di.diff_directories(comparison)

    assert missing_dirs == ["never_uploaded"], missing_dirs
    assert extra_dirs == ["cleaned_up"], extra_dirs
    # A directory with at least one MATCH/SIZE_MISMATCH file is never
    # "missing", even nested ones.
    assert "landed" not in missing_dirs
    assert "landed/sub" not in missing_dirs

    report = di.build_report(
        "test_exp",
        {"upload_complete": False},
        comparison,
    )
    assert report["directory_stats"]["missing"] == ["never_uploaded"]
    assert report["directory_stats"]["extra"] == ["cleaned_up"]
    assert "never_uploaded" in report["sojourner_summary"]

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


def test_upload_info_for_experiment():
    """upload_info_for_experiment must route s1 and s20 to their real
    dm-upload hosts (egressy/redwood, per dm_end_user_1id.sh/
    dm_end_user_20ide.sh) - NOT wherever remote_hosts/checksum_hosts
    already point (zion for s20's DM-read and checksum routing) - and
    build a data_directory distinct from local_root."""
    print("Testing upload_info_for_experiment()...", end=" ")

    config = {
        "settings": {
            "local_bases": {"s1": "~/mnt/s1c", "s20": "~/mnt/s20a"},
            "remote_hosts": {"s1": "egressy", "s20": "zion"},
            "setup_scripts": {"s1": "~/bin/dm_setup_1id.sh dm", "s20": "~/bin/dm_setup_20ide.sh"},
        }
    }

    host, user, setup_script, data_directory = di.upload_info_for_experiment(config, "s1", "pokharel_jul26")
    assert host == "egressy"
    assert user == "s1iduser"
    assert setup_script == "~/bin/dm_setup_1id.sh dm"
    assert data_directory == "/export/s1c/pokharel_jul26"

    host, user, setup_script, data_directory = di.upload_info_for_experiment(config, "s20", "liss_jul26")
    assert host == "redwood", "s20 upload must route to redwood, not zion (where DM reads/checksums go)"
    assert user == "s20iduser"
    assert data_directory == "/net/s20iddata/export/s20a/liss_jul26"

    # An explicit settings.upload_hosts entry overrides the built-in default.
    config["settings"]["upload_hosts"] = {"s1": "kodaly"}
    host, _, _, _ = di.upload_info_for_experiment(config, "s1", "pokharel_jul26")
    assert host == "kodaly"

    # No local_bases entry for the beamline -> can't derive dserv -> None.
    host, user, setup_script, data_directory = di.upload_info_for_experiment(config, "unknown_beamline", "x")
    assert host is None and data_directory is None

    print("✓")


def test_dm_upload_command_quoting():
    """dm_upload_command must shell-quote both arguments - an experiment
    name or data_directory containing a space or shell metacharacter must
    not be able to inject extra arguments into the command shown/run."""
    print("Testing dm_upload_command() quoting...", end=" ")

    cmd = di.dm_upload_command("exp; rm -rf /", "/export/s1c/exp; rm -rf /")
    assert "dm-upload" in cmd
    assert "--experiment=" in cmd and "--data-directory=" in cmd and "--reprocess" in cmd
    # Shell-quoted means the dangerous text sits inside a single-quoted
    # token, not as a bare, shell-interpretable "; rm -rf /".
    assert "'exp; rm -rf /'" in cmd
    assert "'/export/s1c/exp; rm -rf /'" in cmd

    print("✓")


if __name__ == "__main__":
    try:
        test_compare()
        test_find_relocated_files()
        test_build_report()
        test_checksum_worker_passes_through_relocated_files()
        test_diff_directories()
        test_verify_checksums()
        test_save_and_list_records()
        test_scan_local_files()
        test_get_upload_status_mock()
        test_upload_info_for_experiment()
        test_dm_upload_command_quoting()
        print("\nAll tests passed! ✓")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
