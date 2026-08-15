#!/usr/bin/env python3
"""
Data integrity monitor: compare s1c local copies against APS DM (Sojourner) uploads.

Provides lightweight (size/existence only) and on-demand (MD5) file comparison,
upload status tracking, and timestamped JSON records per experiment.

Supports remote SSH execution: if remote_host is configured, DM queries run
on an inside-firewall host and results are retrieved to the local machine.

Usage
-----
  python dm_integrity.py check --config /path/to/config.json --experiment expname
  python dm_integrity.py verify-checksums --config /path/to/config.json --experiment expname
  python dm_integrity.py history --config /path/to/config.json --experiment expname
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

try:
    import dm.cat_web_service.api.datasetCatApi as datasetCatApi
    import dm.cat_web_service.api.fileCatApi as fileCatApi
    import dm.daq_web_service.api.experimentDaqApi as experimentDaqApi
except ImportError:
    # Allow this to fail locally if using remote mode
    datasetCatApi = None
    fileCatApi = None
    experimentDaqApi = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "data_integrity_config.json")
DEFAULT_RECORDS_DIR = os.path.join(SCRIPT_DIR, "records")


# ---------------------------------------------------------------------------
# Remote SSH Execution (for running DM queries from outside firewall)
# ---------------------------------------------------------------------------

def _run_remote_command(remote_host, remote_user, setup_cmd, python_code):
    """Run python_code on remote_host (after sourcing setup_cmd) via SSH,
    returning its stdout parsed as JSON.

    Two separate SSH/shell pitfalls, both avoided here:

    1. ssh doesn't preserve argv boundaries remotely - any trailing arguments
       after the host are joined with spaces into a single string and handed
       to the remote shell, so passing ["bash", "-c", cmd] as three separate
       argv elements silently drops cmd's own quoting once it crosses the
       wire (the remote shell only takes the first word - "source" - as -c's
       argument, treating the rest as bash's positional parameters instead).
       Fixed by collapsing "bash -c <cmd>" into one already shell-quoted
       string before it ever reaches ssh's argv.

    2. python_code is a multi-line Python source string, not shell text.
       Embedding it as `python3 -c {repr(python_code)}` puts Python's own
       quote/escape syntax (from repr()) into a shell argument; the shell
       strips repr()'s quote characters as its own quoting and does not
       interpret its \\n escapes, so python3 ends up receiving a literal
       backslash-n instead of a newline - a SyntaxError. Fixed by running
       `python3 -` and piping python_code in over stdin, so it never has to
       survive a shell-quoting round trip at all.
    """
    if remote_user:
        remote_spec = f"{remote_user}@{remote_host}"
    else:
        remote_spec = remote_host

    remote_cmd = "bash -c {}".format(shlex.quote(setup_cmd + " && python3 -"))

    try:
        result = subprocess.run(
            ["ssh", remote_spec, remote_cmd],
            input=python_code,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"Remote command failed: {result.stderr}")
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Remote command returned invalid JSON: {result.stdout}")
    except Exception as e:
        raise RuntimeError(f"SSH execution failed: {e}")


def get_recent_experiments(limit=10, remote_host=None, remote_user=None, station_configs=None):
    """
    Query DM for recent experiments from multiple beamlines.
    Returns list of (experiment_name, beamline_name) tuples, sorted by recency (most recent first).

    station_configs: list of dicts like [
        {"name": "s1", "setup_script": "/dm/1id/etc/dm.setup.sh", "remote_host": "egressy"},
        {"name": "s20", "setup_script": "/dm/20id/etc/dm.setup.sh", "remote_host": "zion"}
    ]
    """
    if station_configs is None:
        station_configs = [{"name": "s1", "setup_script": "/dm/1id/etc/dm.setup.sh"}]

    all_experiments = []
    per_station_limit = max(1, limit // len(station_configs))

    for station_config in station_configs:
        station_name = station_config.get("name", "unknown")
        setup_script = station_config.get("setup_script", "/dm/1id/etc/dm.setup.sh")
        # Allow per-station remote_host override
        station_remote_host = station_config.get("remote_host", remote_host)

        if station_remote_host:
            python_code = f"""
import json
import dm.daq_web_service.api.experimentDaqApi as experimentDaqApi
try:
    api = experimentDaqApi.ExperimentDaqApi()
    records = api.listUploadRecords(queryDict={{}})

    # Group by experiment name, keep MOST RECENT upload record per experiment.
    # listUploadRecords() records have no 'timestamp' field - the real field
    # is 'startTime' (an epoch float, when that upload/DAQ job started).
    exp_dict = {{}}
    for record in records:
        exp_name = record.get('experimentName', 'Unknown')
        exp_start = record.get('startTime', 0)
        # Only update if this is newer than what we have
        if exp_name not in exp_dict or exp_start > exp_dict[exp_name].get('startTime', 0):
            exp_dict[exp_name] = record

    # Sort by upload start time (most recent first)
    sorted_exps = sorted(exp_dict.items(), key=lambda x: x[1].get('startTime', 0), reverse=True)
    result = [(exp[0], '{station_name}', exp[1].get('startTime', 0)) for exp in sorted_exps]
    print(json.dumps(result))
except Exception as e:
    print(json.dumps([]))
"""
            # Use beamline-specific user if available
            beamline_user = remote_user
            if station_name == "s1":
                beamline_user = "s1iduser"
            elif station_name == "s20":
                beamline_user = "s20iduser"

            setup_cmd = f"source {setup_script} && conda activate dm-user"
            # See _run_remote_command's docstring for both pitfalls this
            # avoids: collapsing "bash -c <cmd>" into one shell-quoted argv
            # element (ssh flattens trailing argv with spaces otherwise), and
            # piping python_code over stdin to `python3 -` instead of
            # embedding it as `python3 -c {repr(python_code)}` (repr()'s
            # quotes/escapes are Python syntax, not shell syntax - the shell
            # strips them without interpreting \n, so python3 would receive a
            # literal backslash-n and fail with a SyntaxError).
            remote_cmd = "bash -c {}".format(shlex.quote(setup_cmd + " && python3 -"))
            try:
                if beamline_user:
                    remote_spec = f"{beamline_user}@{station_remote_host}"
                else:
                    remote_spec = station_remote_host

                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=10", "-o", "ControlMaster=auto",
                     "-o", "ControlPath=~/.ssh/control-%h-%p-%r", "-o", "ControlPersist=300",
                     remote_spec, remote_cmd],
                    input=python_code,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    experiments = json.loads(result.stdout)
                    # Already sorted by recency (most recent first) by the
                    # remote query - cap per station so one busy beamline
                    # can't crowd the other out of the final merged list.
                    all_experiments.extend(experiments[:per_station_limit])
                else:
                    print(f"SSH error for {station_name}: {result.stderr}", file=sys.stderr)
            except Exception as e:
                print(f"SSH exception for {station_name}: {e}", file=sys.stderr)
                continue
        else:
            # Local execution
            if experimentDaqApi is None:
                continue

            try:
                api = experimentDaqApi.ExperimentDaqApi()
                records = api.listUploadRecords(queryDict={})

                # Group by experiment name, keep MOST RECENT upload record per
                # experiment. listUploadRecords() records have no 'timestamp'
                # field - the real field is 'startTime' (an epoch float, when
                # that upload/DAQ job started).
                exp_dict = {}
                for record in records:
                    exp_name = record.get('experimentName', 'Unknown')
                    exp_start = record.get('startTime', 0)
                    # Only update if this is newer than what we have
                    if exp_name not in exp_dict or exp_start > exp_dict[exp_name].get('startTime', 0):
                        exp_dict[exp_name] = record

                # Sort by upload start time (most recent first), capped per
                # station so one busy beamline can't crowd the other out.
                sorted_exps = sorted(exp_dict.items(), key=lambda x: x[1].get('startTime', 0), reverse=True)
                capped = sorted_exps[:per_station_limit]
                all_experiments.extend([(exp[0], station_name, exp[1].get('startTime', 0)) for exp in capped])
            except:
                continue

    # Each station's own segment is already sorted by recency (most recent
    # first) from the per-station capping above. Deliberately not doing a
    # second, global sort-by-date here: that would interleave stations by
    # date instead of grouping by station (station_configs' own order, e.g.
    # s1 before s20) with recency only as the tie-breaker within each group.
    return [(name, station) for name, station, _ in all_experiments[:limit]]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path):
    """Load config JSON. Returns dict with 'settings' and 'experiments' keys."""
    with open(path) as f:
        config = json.load(f)

    if "settings" not in config:
        config["settings"] = {}
    config["settings"].setdefault("records_dir", DEFAULT_RECORDS_DIR)

    return config


def get_upload_status(experiment_name, station_name="SOJOURNER", remote_host=None, remote_user=None,
                       setup_script="/dm/1id/etc/dm.setup.sh"):
    """
    Query DM upload status. Returns dict with keys:
    status (str), n_files (int), n_completed (int), n_errors (int),
    upload_complete (bool).

    If remote_host is provided, executes this query on the remote host via
    SSH, sourcing setup_script first - this MUST match the target beamline
    (e.g. ~/bin/dm_setup_20ide.sh for an s20 experiment); the 1-ID default
    only happens to work when querying s1.
    """
    if remote_host:
        # Execute remotely
        python_code = f"""
import json
import dm.daq_web_service.api.experimentDaqApi as experimentDaqApi
try:
    api = experimentDaqApi.ExperimentDaqApi()
    records = api.listUploadRecords(queryDict={{"experimentName": "{experiment_name}"}})
    if not records:
        result = {{"status": "unknown", "n_files": 0, "n_completed": 0, "n_errors": 0, "upload_complete": False}}
    else:
        latest = records[-1]
        status = latest.get("status", "unknown")
        n_files = latest.get("nFiles", 0)
        n_completed = latest.get("nCompletedFiles", 0)
        n_errors = latest.get("nProcessingErrors", 0)
        upload_complete = status == "done" and n_errors == 0
        result = {{"status": status, "n_files": n_files, "n_completed": n_completed, "n_errors": n_errors, "upload_complete": upload_complete}}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"status": "error", "n_files": 0, "n_completed": 0, "n_errors": -1, "upload_complete": False, "error_msg": str(e)}}))
"""
        setup_cmd = f"source {setup_script} && conda activate dm-user"
        return _run_remote_command(remote_host, remote_user, setup_cmd, python_code)

    # Local execution
    if experimentDaqApi is None:
        return {
            "status": "error",
            "n_files": 0,
            "n_completed": 0,
            "n_errors": -1,
            "upload_complete": False,
            "error_msg": "DM API not available locally. Configure remote_host in settings.",
        }

    try:
        api = experimentDaqApi.ExperimentDaqApi()
        records = api.listUploadRecords(queryDict={"experimentName": experiment_name})
    except Exception as e:
        return {
            "status": "error",
            "n_files": 0,
            "n_completed": 0,
            "n_errors": -1,
            "upload_complete": False,
            "error_msg": str(e),
        }

    if not records:
        return {
            "status": "unknown",
            "n_files": 0,
            "n_completed": 0,
            "n_errors": 0,
            "upload_complete": False,
        }

    latest = records[-1]
    status = latest.get("status", "unknown")
    n_files = latest.get("nFiles", 0)
    n_completed = latest.get("nCompletedFiles", 0)
    n_errors = latest.get("nProcessingErrors", 0)

    upload_complete = status == "done" and n_errors == 0

    return {
        "status": status,
        "n_files": n_files,
        "n_completed": n_completed,
        "n_errors": n_errors,
        "upload_complete": upload_complete,
    }


def get_catalog_files(experiment_name, dataset_name=None, station_name="SOJOURNER", remote_host=None, remote_user=None,
                       setup_script="/dm/1id/etc/dm.setup.sh"):
    """
    Fetch DM catalog file metadata.
    Returns dict {experimentFilePath: {"size": fileSize, "md5": md5Sum}}.

    If remote_host is provided, executes this query on the remote host via
    SSH, sourcing setup_script first - see get_upload_status's docstring on
    why this must match the target beamline.
    """
    if remote_host:
        # Execute remotely
        dataset_arg = f'"{dataset_name}"' if dataset_name else "None"
        python_code = f"""
import json
import dm.cat_web_service.api.datasetCatApi as datasetCatApi
import dm.cat_web_service.api.fileCatApi as fileCatApi

def accumulate(result, files):
    for f in files:
        path = f.get("experimentFilePath", "")
        size = f.get("fileSize", 0)
        md5 = f.get("md5Sum", "")
        if path:
            result[path] = {{"size": size, "md5": md5}}

try:
    result = {{}}
    if {dataset_arg}:
        files = datasetCatApi.DatasetCatApi().getExperimentDatasetFiles("{experiment_name}", {dataset_arg}) or []
        accumulate(result, files)
    else:
        # getExperimentFiles() caps results at `limit` per call (500000
        # default) - page through skip/limit so an experiment with more
        # files than that doesn't come back silently truncated (looking
        # like everything past the cutoff is LOCAL_ONLY).
        api = fileCatApi.FileCatApi()
        page_size = 100000
        skip = 0
        while True:
            files = api.getExperimentFiles("{experiment_name}", skip=skip, limit=page_size) or []
            accumulate(result, files)
            if len(files) < page_size:
                break
            skip += page_size
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{}}))
"""
        setup_cmd = f"source {setup_script} && conda activate dm-user"
        return _run_remote_command(remote_host, remote_user, setup_cmd, python_code)

    # Local execution
    if fileCatApi is None or datasetCatApi is None:
        return {}

    result = {}
    try:
        if dataset_name:
            files = datasetCatApi.DatasetCatApi().getExperimentDatasetFiles(experiment_name, dataset_name) or []
            _accumulate_catalog_files(result, files)
        else:
            # getExperimentFiles() caps results at `limit` per call (500000
            # default) - an experiment with more files than that would
            # silently look truncated (missing files reported as
            # LOCAL_ONLY) without paging through skip/limit like this, the
            # same reason the old dm_data_integrity.sh script paginated
            # dm-get-experiment-files manually in 100k chunks.
            api = fileCatApi.FileCatApi()
            page_size = 100000
            skip = 0
            while True:
                files = api.getExperimentFiles(experiment_name, skip=skip, limit=page_size) or []
                _accumulate_catalog_files(result, files)
                if len(files) < page_size:
                    break
                skip += page_size
    except Exception:
        return {}

    return result


def _accumulate_catalog_files(result, files):
    for f in files:
        path = f.get("experimentFilePath", "")
        size = f.get("fileSize", 0)
        md5 = f.get("md5Sum", "")
        if path:
            result[path] = {"size": size, "md5": md5}

    return result


_NON_EXPERIMENT_DIR_PREFIXES = ("__", ".")

# Real experiment directories (the actual expid) are exactly
# <piname>_<mon><yy> (e.g. "park_may25", "parraga_midas_setup_jun24") - NOT
# suffixed variants like "brown_jul26_bc" or "xzhang_jul26_analysis", which
# are dataset/analysis subfolders *for* an experiment, not the experiment
# itself. s1c/s20a also hold plenty of other non-experiment folders
# (utility/admin dirs, network shares, one-off docs) that don't fit this
# shape at all - requiring an exact match is a much better filter than
# mtime alone.
_EXPERIMENT_NAME_RE = re.compile(
    r"^.+_(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(\d{2})$",
    re.IGNORECASE,
)

_MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def discover_local_experiments(base_dir, limit=3):
    """List the `limit` most recent experiment subdirectories of base_dir
    (e.g. s1c/s20a staging areas), by the date encoded in each name.

    This is a fast, DM-independent proxy for "recent/active experiments" -
    unlike Sojourner's upload records, it doesn't depend on which VM/station
    an upload routed through, doesn't require SSH, and reflects an
    experiment the moment there's local data at all, even before anything's
    been uploaded.

    Recency is taken from the <mon><yy> encoded in the name (e.g. "jul26"),
    NOT directory mtime - mtime turned out to be unreliable here, since
    something (a backup/archival pass, most likely) periodically touches a
    subdirectory inside old experiment folders, making a year-old
    experiment's top-level mtime look newer than one from last week. The
    name's own date doesn't have that problem. mtime is only used to break
    ties between experiments naming the same month.

    Returns [(name, local_root), ...] sorted most-recent first. Only
    considers directories matching _EXPERIMENT_NAME_RE (skips
    administrative folders, dotfiles, and other non-experiment directories
    that live alongside real ones in these mounts) - an experiment that
    doesn't follow the naming convention won't be auto-discovered, but can
    still be added explicitly via the config's "experiments" list.
    """
    if not os.path.isdir(base_dir):
        return []

    entries = []
    for name in os.listdir(base_dir):
        if name.startswith(_NON_EXPERIMENT_DIR_PREFIXES):
            continue
        match = _EXPERIMENT_NAME_RE.match(name)
        if not match:
            continue
        full_path = os.path.join(base_dir, name)
        try:
            st = os.stat(full_path)
        except OSError:
            continue
        if not os.path.isdir(full_path):
            continue

        month = _MONTH_NUMBERS[match.group(1).lower()]
        year = 2000 + int(match.group(2))
        name_date_key = year * 12 + month
        entries.append((name, full_path, name_date_key, st.st_mtime))

    entries.sort(key=lambda e: (e[2], e[3]), reverse=True)
    return [(name, path) for name, path, _, _ in entries[:limit]]


def scan_local_files(local_root):
    """
    Recursively scan local_root for all files.
    Returns dict {relative_path: {"size": st_size, "mtime": st_mtime}}.
    """
    result = {}

    if not os.path.isdir(local_root):
        return result

    for dirpath, dirnames, filenames in os.walk(local_root):
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            try:
                stat = os.stat(full_path)
                rel_path = os.path.relpath(full_path, local_root)
                result[rel_path] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            except (OSError, IOError):
                pass

    return result


def compare(local_files, catalog_files):
    """
    Lightweight comparison (size/existence only, no hashing).
    Returns dict {path: status} where status is one of:
    MATCH, SIZE_MISMATCH, LOCAL_ONLY, REMOTE_ONLY.
    """
    result = {}
    all_paths = set(local_files.keys()) | set(catalog_files.keys())

    for path in all_paths:
        in_local = path in local_files
        in_catalog = path in catalog_files

        if in_local and in_catalog:
            local_size = local_files[path].get("size", 0)
            catalog_size = catalog_files[path].get("size", 0)
            if local_size == catalog_size:
                result[path] = "MATCH"
            else:
                result[path] = "SIZE_MISMATCH"
        elif in_local:
            result[path] = "LOCAL_ONLY"
        else:
            result[path] = "REMOTE_ONLY"

    return result


def verify_checksums(local_root, catalog_files, paths):
    """
    Explicit checksum verification (MD5) for specific paths.
    Returns dict {path: "CHECKSUM_MATCH" | "CHECKSUM_MISMATCH"}.
    """
    result = {}

    for path in paths:
        if path not in catalog_files:
            continue

        full_path = os.path.join(local_root, path)
        if not os.path.isfile(full_path):
            result[path] = "CHECKSUM_UNKNOWN"
            continue

        expected_md5 = catalog_files[path].get("md5", "").lower()
        if not expected_md5:
            result[path] = "CHECKSUM_UNKNOWN"
            continue

        try:
            md5_hash = hashlib.md5()
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            computed_md5 = md5_hash.hexdigest()

            if computed_md5 == expected_md5:
                result[path] = "CHECKSUM_MATCH"
            else:
                result[path] = "CHECKSUM_MISMATCH"
        except (OSError, IOError):
            result[path] = "CHECKSUM_ERROR"

    return result


def build_report(experiment_name, upload_status, comparison, checksum_results=None):
    """
    Build summary report.
    Returns dict with experiment info, file stats, and recommend_deletion flag.
    """
    checksum_results = checksum_results or {}

    match_count = sum(1 for s in comparison.values() if s == "MATCH")
    size_mismatch_count = sum(1 for s in comparison.values() if s == "SIZE_MISMATCH")
    local_only_count = sum(1 for s in comparison.values() if s == "LOCAL_ONLY")
    remote_only_count = sum(1 for s in comparison.values() if s == "REMOTE_ONLY")
    checksum_mismatch_count = sum(1 for s in checksum_results.values() if s == "CHECKSUM_MISMATCH")

    total_files = len(comparison)
    good_files = match_count
    bad_files = size_mismatch_count + local_only_count + remote_only_count + checksum_mismatch_count

    recommend_deletion = (
        upload_status.get("upload_complete", False) and
        local_only_count == 0 and
        size_mismatch_count == 0 and
        remote_only_count == 0 and
        checksum_mismatch_count == 0
    )

    # A plain answer to "did the local files land on Sojourner at all" -
    # distinct from recommend_deletion, which additionally requires DM to
    # report the *upload* itself as fully complete. An experiment can be
    # NOT_ON_SOJOURNER (still just LOCAL_ONLY - nothing in the DM catalog
    # yet, the common case for a currently-running experiment) well before
    # "safe to delete" is ever a relevant question.
    if total_files == 0:
        sojourner_status = "NO_LOCAL_FILES"
        sojourner_summary = "No local files found to compare"
    elif local_only_count == total_files:
        sojourner_status = "NOT_ON_SOJOURNER"
        sojourner_summary = "Not on Sojourner yet - no local files found in the DM catalog"
    elif match_count == total_files and remote_only_count == 0:
        sojourner_status = "FULLY_LANDED"
        sojourner_summary = "All local files have landed on Sojourner"
    else:
        sojourner_status = "PARTIALLY_LANDED"
        sojourner_summary = f"Partially landed on Sojourner: {match_count}/{total_files} files match"

    report = {
        "experiment_name": experiment_name,
        "timestamp": time.time(),
        "upload_status": upload_status,
        "file_stats": {
            "total": total_files,
            "good": good_files,
            "bad": bad_files,
            "match": match_count,
            "size_mismatch": size_mismatch_count,
            "local_only": local_only_count,
            "remote_only": remote_only_count,
            "checksum_mismatch": checksum_mismatch_count,
        },
        "comparison": comparison,
        "checksum_results": checksum_results,
        "sojourner_status": sojourner_status,
        "sojourner_summary": sojourner_summary,
        "recommend_deletion": recommend_deletion,
        "recommendation_reason": (
            "Upload complete and all files match (checksums verified)"
            if recommend_deletion and checksum_results
            else "Upload complete and all files match (size-only check)"
            if recommend_deletion
            else "Upload not complete or files differ"
        ),
    }

    return report


def _year_for_experiment(experiment_name):
    """Best-effort experiment year from the mon/yy encoded in the expid (see
    _EXPERIMENT_NAME_RE) - e.g. 'pokharel_jul26' -> '2026'. None if the name
    doesn't follow that convention (a manually-configured experiment with an
    arbitrary name, say)."""
    match = _EXPERIMENT_NAME_RE.match(experiment_name)
    if not match:
        return None
    return str(2000 + int(match.group(2)))


def _exp_records_dirs(records_dir, experiment_name):
    """Every directory that might hold experiment_name's records: the
    year-organized path (preferred; where new records get saved) and the
    old flat path (kept findable for records saved before per-year
    organization existed, or for names we can't date)."""
    dirs = []
    year = _year_for_experiment(experiment_name)
    if year:
        dirs.append(os.path.join(records_dir, year, experiment_name))
    dirs.append(os.path.join(records_dir, experiment_name))
    return dirs


def save_record(records_dir, experiment_name, report):
    """
    Save report as JSON with timestamp filename, organized by the
    experiment's run year when it can be determined from the expid (e.g.
    records_dir/2026/pokharel_jul26/<timestamp>.json) - mirrors the
    per-cycle folders (2020_3/, 2019_2/, ...) the old MATLAB-based workflow
    used. Falls back to records_dir/<experiment_name>/ directly when the
    name doesn't encode a year.
    """
    exp_records_dir = _exp_records_dirs(records_dir, experiment_name)[0]
    Path(exp_records_dir).mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    filepath = os.path.join(exp_records_dir, f"{timestamp}.json")

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    return filepath


def list_records(records_dir, experiment_name):
    """
    List past records for an experiment, sorted by timestamp (oldest first).
    Checks both the year-organized location and the old flat location, so
    records saved before per-year organization existed are still found.
    Returns list of (timestamp, filepath) tuples.
    """
    records = []
    for exp_records_dir in _exp_records_dirs(records_dir, experiment_name):
        if not os.path.isdir(exp_records_dir):
            continue
        for filename in os.listdir(exp_records_dir):
            if filename.endswith(".json"):
                try:
                    timestamp = int(filename.rstrip(".json"))
                    filepath = os.path.join(exp_records_dir, filename)
                    records.append((timestamp, filepath))
                except ValueError:
                    pass

    records.sort(key=lambda x: x[0])
    return records


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Data integrity monitor (local s1c vs. APS DM)")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="Path to config JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Lightweight compare + save record")
    check_parser.add_argument("--experiment", required=True, help="Experiment name")
    check_parser.add_argument("--dataset", help="Dataset name (optional)")

    verify_parser = subparsers.add_parser("verify-checksums", help="Verify MD5 checksums")
    verify_parser.add_argument("--experiment", required=True, help="Experiment name")
    verify_parser.add_argument("--dataset", help="Dataset name (optional)")

    history_parser = subparsers.add_parser("history", help="Show past records")
    history_parser.add_argument("--experiment", required=True, help="Experiment name")

    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    config = load_config(args.config)
    settings = config.get("settings", {})
    records_dir = settings.get("records_dir", DEFAULT_RECORDS_DIR)
    station_name = settings.get("station_name", "SOJOURNER")
    remote_host = settings.get("remote_host")
    remote_user = settings.get("remote_user")

    exp_config = None
    for exp in config.get("experiments", []):
        if exp.get("name") == args.experiment:
            exp_config = exp
            break

    if not exp_config:
        sys.exit(f"Experiment '{args.experiment}' not found in config")

    local_root = exp_config.get("local_root")
    if not local_root:
        sys.exit(f"No local_root configured for experiment '{args.experiment}'")

    if not remote_host and experimentDaqApi is None:
        sys.exit(
            "dm Python API is not available locally and no remote_host configured.\n"
            "Either:\n"
            "  1. Source dm.setup.sh and activate dm-user environment\n"
            "  2. Configure 'remote_host' in settings to run DM queries via SSH\n"
        )

    if args.command == "check":
        upload_status = get_upload_status(args.experiment, station_name, remote_host, remote_user)
        catalog_files = get_catalog_files(args.experiment, args.dataset, station_name, remote_host, remote_user)
        local_files = scan_local_files(local_root)
        comparison = compare(local_files, catalog_files)

        report = build_report(args.experiment, upload_status, comparison)
        save_record(records_dir, args.experiment, report)

        print(f"Experiment: {args.experiment}")
        print(f"Upload status: {upload_status['status']}")
        print(f"Files: {report['file_stats']['good']} good / {report['file_stats']['bad']} bad")
        print(f"Recommend deletion: {report['recommend_deletion']}")

    elif args.command == "verify-checksums":
        upload_status = get_upload_status(args.experiment, station_name, remote_host, remote_user)
        catalog_files = get_catalog_files(args.experiment, args.dataset, station_name, remote_host, remote_user)
        local_files = scan_local_files(local_root)
        comparison = compare(local_files, catalog_files)

        paths_to_verify = [p for p, s in comparison.items() if s == "MATCH"]
        checksum_results = verify_checksums(local_root, catalog_files, paths_to_verify)

        report = build_report(args.experiment, upload_status, comparison, checksum_results)
        save_record(records_dir, args.experiment, report)

        print(f"Experiment: {args.experiment}")
        print(f"Checksums verified: {sum(1 for s in checksum_results.values() if s == 'CHECKSUM_MATCH')} match")
        print(f"Checksums failed: {sum(1 for s in checksum_results.values() if s == 'CHECKSUM_MISMATCH')} mismatch")
        print(f"Recommend deletion: {report['recommend_deletion']}")

    elif args.command == "history":
        records = list_records(records_dir, args.experiment)
        if not records:
            print(f"No records found for experiment '{args.experiment}'")
            return 0

        print(f"Records for experiment '{args.experiment}':")
        for timestamp, filepath in records:
            with open(filepath) as f:
                record = json.load(f)
            stats = record["file_stats"]
            rec_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            print(f"  {rec_time}: {stats['good']} good / {stats['bad']} bad "
                  f"(recommend: {record['recommend_deletion']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
