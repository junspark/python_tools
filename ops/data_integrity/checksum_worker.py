#!/usr/bin/env python3
"""
Standalone MD5 checksum verification worker - runs detached (via
`systemd-run --user` on zion) so a Verify MD5 job survives the launching
GUI closing.

Stdlib-only - no PyQt, no `dm` package. Reuses dm_integrity.py's
verify_checksums/build_report/save_record directly (this script lives next
to dm_integrity.py on the same shared filesystem, so `sys.path.insert` is
enough - no packaging/staging needed).

Usage
-----
  python3 checksum_worker.py --job-spec /path/to/job.json --status-file /path/to/status.json

Job spec (written by the GUI before launching, see dm_integrity_gui.py):
  experiment_name, beamline, local_root (already canonicalized),
  upload_status, catalog_files, comparison (compare()'s size-based result -
  build_report needs this alongside checksum_results), paths_to_verify,
  relocated_files (find_relocated_files()'s output, computed by the GUI
  since it has local_files in scope and this worker only gets local_root -
  read via .get(..., []) so a job spec from before this key existed still
  runs), records_dir, status_dirs (list - both beamlines', for aggregate
  peer counting), cpu_budget.

Status file is updated in place (atomic write) as the job progresses -
state machine QUEUED -> RUNNING -> DONE|FAILED|CANCELLED. The GUI writes
the initial QUEUED entry; this script preserves those fields (queued_at,
unit_name) and layers its own updates on top, so nothing GUI-written is
lost.
"""

import argparse
import json
import os
import resource
import signal
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import dm_integrity as di

STALE_PEER_SEC = 30       # a RUNNING status file not updated in this long doesn't count as an active peer
STATUS_WRITE_INTERVAL_SEC = 2
PEER_COUNT_CACHE_SEC = 1.0    # avoid re-globbing both status dirs on every single file for large jobs
MAX_CATCHUP_SLEEP_SEC = 5.0   # cap how much a single throttle check can demand, however far behind fair_share it thinks it is
CANCEL_CHECK_INTERVAL_SEC = 0.5   # sleep in chunks this small so SIGTERM is noticed promptly even mid-throttle
STATUS_SUFFIX = ".json"   # job specs use a distinct, non-.json extension specifically so this glob can't match them - see _count_active_peers

_cancelled = False


def _handle_sigterm(signum, frame):
    global _cancelled
    _cancelled = True


def _load_status(status_file):
    try:
        with open(status_file) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _count_active_peers(status_dirs, own_status_file):
    """Count RUNNING, recently-updated jobs across all given status
    directories (both beamlines' - this is what makes the CPU budget a
    genuine cross-beamline aggregate rather than per-user). Includes this
    job itself once it has written its own RUNNING status.

    Only ever reads small status files (STATUS_SUFFIX) - job specs
    (JOB_SPEC_SUFFIX) live in the same directory and can be many MB for a
    large experiment's full catalog. Confirmed directly: an earlier
    version's naive "*.json" glob also matched a 17MB job spec file and
    re-read/re-parsed it on every single progress callback (once per
    hashed file), which alone was enough to stall two concurrent jobs
    completely - not a throttle-math bug, a real I/O bug. Both the
    suffix-based filter here and job specs using a distinct extension
    (not ending in .json at all - see dm_integrity_gui.py's
    _ChecksumLaunchWorker) guard against this independently.
    """
    now = time.time()
    count = 0
    for status_dir in status_dirs:
        try:
            names = os.listdir(status_dir)
        except OSError:
            continue
        for name in names:
            if not name.endswith(STATUS_SUFFIX):
                continue
            path = os.path.join(status_dir, name)
            data = _load_status(path)
            if data.get("state") == "RUNNING" and (now - data.get("updated_at", 0)) < STALE_PEER_SEC:
                count += 1
    return max(count, 1)


class ChecksumJob:
    def __init__(self, job_spec, status_file):
        self.spec = job_spec
        self.status_file = status_file
        self.status = _load_status(status_file)
        self.status.setdefault("schema_version", 1)
        self.status["experiment_name"] = job_spec["experiment_name"]
        self.status["beamline"] = job_spec["beamline"]
        self.status["pid"] = os.getpid()

        self._throttle_start_wall = time.time()
        self._throttle_start_cpu = self._cpu_time()
        self._last_status_write = 0.0
        self._peer_count_cached_at = 0.0
        self._peer_count_cached_value = 1

    def _cpu_time(self):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_utime + usage.ru_stime

    def _write_status(self, force=False):
        now = time.time()
        if not force and (now - self._last_status_write) < STATUS_WRITE_INTERVAL_SEC:
            return
        self.status["updated_at"] = now
        di._atomic_write_json(self.status_file, self.status)
        self._last_status_write = now

    def mark_running(self):
        self.status["state"] = "RUNNING"
        self.status["started_at"] = time.time()
        self.status["total_files"] = len(self.spec.get("paths_to_verify", []))
        self.status["checked_files"] = 0
        self.status["match_count"] = 0
        self.status["mismatch_count"] = 0
        self.status["unknown_count"] = 0
        self.status["error_count"] = 0
        self.status["report_path"] = None
        self.status["error_message"] = None
        self._write_status(force=True)

    def progress_cb(self, path, index, total, result):
        self.status["checked_files"] = index
        if result == "CHECKSUM_MATCH":
            self.status["match_count"] += 1
        elif result == "CHECKSUM_MISMATCH":
            self.status["mismatch_count"] += 1
        elif result == "CHECKSUM_ERROR":
            self.status["error_count"] += 1
        else:
            self.status["unknown_count"] += 1

        self._write_status()
        self._throttle()

        if _cancelled:
            self.status["state"] = "CANCELLED"
            self.status["finished_at"] = time.time()
            self._write_status(force=True)
            sys.exit(0)

    def _throttle(self):
        """Cooperative duty-cycle governor: pace this job's own CPU usage
        to a fair share of the configured aggregate budget, recomputed
        against however many peer jobs (across both beamlines) are
        currently active. Real kernel CPUQuota enforcement isn't available
        here (the `cpu` cgroup controller isn't delegated to user sessions
        on zion) - this is the actual enforcement mechanism, not a backup.

        Deliberately reactive, not cumulative-since-job-start: an earlier
        version measured cpu_used/wall_elapsed against the job's whole
        lifetime, so when fair_share dropped (a peer job started),
        "catching up" to the new ratio could demand tens of seconds of
        sleep in one shot - confirmed directly, a job stalled for 2+
        minutes with zero progress this way, and didn't even respond to
        SIGTERM promptly since the single time.sleep() call wasn't
        interrupted. Instead: measure only the CPU/wall time since the
        *last* throttle check, react to that alone, and sleep in small
        chunks so a cancellation is noticed within CANCEL_CHECK_INTERVAL_SEC
        regardless of how much total sleep is warranted.
        """
        cpu_budget = self.spec.get("cpu_budget", 0.20)
        now = time.time()
        if (now - self._peer_count_cached_at) >= PEER_COUNT_CACHE_SEC:
            status_dirs = self.spec.get("status_dirs", [])
            self._peer_count_cached_value = _count_active_peers(status_dirs, self.status_file)
            self._peer_count_cached_at = now
        fair_share = max(cpu_budget / self._peer_count_cached_value, 0.01)

        wall_elapsed = now - self._throttle_start_wall
        cpu_used = self._cpu_time() - self._throttle_start_cpu
        # Reset the window for next time regardless of what we do below -
        # this is what bounds the "debt" to at most one window's worth.
        self._throttle_start_wall = now
        self._throttle_start_cpu = self._cpu_time()

        if wall_elapsed <= 0:
            return

        current_ratio = cpu_used / wall_elapsed
        if current_ratio <= fair_share:
            return

        target_wall = cpu_used / fair_share
        sleep_needed = min(target_wall - wall_elapsed, MAX_CATCHUP_SLEEP_SEC)
        while sleep_needed > 0 and not _cancelled:
            chunk = min(sleep_needed, CANCEL_CHECK_INTERVAL_SEC)
            time.sleep(chunk)
            sleep_needed -= chunk

    def mark_done(self, report_path):
        self.status["state"] = "DONE"
        self.status["finished_at"] = time.time()
        self.status["report_path"] = report_path
        self._write_status(force=True)

    def mark_failed(self, error_message):
        self.status["state"] = "FAILED"
        self.status["finished_at"] = time.time()
        self.status["error_message"] = str(error_message)[:2000]
        self._write_status(force=True)


def run(job_spec_path, status_file):
    signal.signal(signal.SIGTERM, _handle_sigterm)

    with open(job_spec_path) as f:
        spec = json.load(f)

    job = ChecksumJob(spec, status_file)
    job.mark_running()

    try:
        experiment_name = spec["experiment_name"]
        local_root = spec["local_root"]
        catalog_files = spec["catalog_files"]
        comparison = spec["comparison"]
        paths_to_verify = spec["paths_to_verify"]
        upload_status = spec["upload_status"]
        records_dir = spec["records_dir"]
        # .get(), not spec[...]: a job launched by an older
        # _ChecksumLaunchWorker (before relocated_files existed) has no
        # such key - defaults to [] the same way build_report's own
        # relocated_files=None default does, so an in-flight upgrade never
        # crashes a running job.
        relocated_files = spec.get("relocated_files", [])

        checksum_results = di.verify_checksums(
            local_root, catalog_files, paths_to_verify, progress_cb=job.progress_cb)

        report = di.build_report(experiment_name, upload_status, comparison, checksum_results, relocated_files)
        report_path = di.save_record(records_dir, experiment_name, report)

        job.mark_done(report_path)
        return 0
    except Exception as e:
        job.mark_failed(e)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-spec", required=True)
    parser.add_argument("--status-file", required=True)
    args = parser.parse_args()
    sys.exit(run(args.job_spec, args.status_file))
