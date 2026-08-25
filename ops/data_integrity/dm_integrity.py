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
import stat
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
import remote_job as rj

try:
    import dm.cat_web_service.api.datasetCatApi as datasetCatApi
    import dm.cat_web_service.api.fileCatApi as fileCatApi
    import dm.daq_web_service.api.experimentDaqApi as experimentDaqApi
except ImportError:
    # Allow this to fail locally if using remote mode
    datasetCatApi = None
    fileCatApi = None
    experimentDaqApi = None


DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "data_integrity_config.json")
DEFAULT_RECORDS_DIR = os.path.join(SCRIPT_DIR, "records")


# ---------------------------------------------------------------------------
# Remote SSH Execution (for running DM queries from outside firewall)
# ---------------------------------------------------------------------------

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


def save_config(config, path):
    """Write config back to path - used for explicit user edits (e.g. the
    GUI's "Add experiment..." dialog persisting a manually-tracked
    experiment) rather than anything auto-discovered, which stays
    in-memory only (see DataIntegrityPanel._register_local_root)."""
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Checksum job routing & shared records/status (per beamline, not per user)
# ---------------------------------------------------------------------------

# canonical_local_root, _atomic_write_json, write_remote_file,
# launch_checksum_job, lock_dir, acquire_remote_lock, release_remote_lock
# used to be defined here directly - now thin wrappers around remote_job.py
# (see that module's docstring), extracted so pv_logger.py's persistent
# jobs can reuse the same SSH/locking plumbing instead of a second copy.
# Kept as wrappers with their original names/signatures, rather than
# updating every di.<name> call site in dm_integrity_gui.py, since this is
# a behavior-preserving refactor of already-relied-upon production code.
canonical_local_root = rj.canonical_path
run_shell_command = rj.run_shell_command


_BEAMLINE_DM_DEFAULTS = {
    "s1": ("egressy", "s1iduser", "~/bin/dm_setup_1id.sh dm"),
    "s20": ("zion", "s20iduser", "~/bin/dm_setup_20ide.sh"),
}


def remote_info_for_beamline(config, beamline):
    """(remote_host, remote_user, setup_script) for beamline's *DM catalog*
    queries (get_upload_status/get_catalog_files), from settings.remote_hosts/
    setup_scripts, falling back to the same per-beamline defaults regardless
    of whether those settings keys are present - so a minimal or stale
    config still reaches the right DM instance over SSH instead of silently
    falling back to local execution (which returns empty/error results on
    any host without a local dm install, not the beamline's actual upload
    status). Shared by the GUI (DataIntegrityPanel._remote_info_for_beamline)
    and the CLI (main()) so both route the same way - distinct from
    remote_identity_for_beamline, which is about where checksum jobs
    *execute* (always zion), not where DM itself is queried from.
    """
    settings = config.get("settings", {})
    remote_hosts = settings.get("remote_hosts", {})
    setup_scripts = settings.get("setup_scripts", {})
    default_host, default_user, default_script = _BEAMLINE_DM_DEFAULTS.get(
        beamline, (None, None, "/dm/1id/etc/dm.setup.sh"))
    remote_host = remote_hosts.get(beamline, default_host)
    setup_script = setup_scripts.get(beamline, default_script)
    return remote_host, default_user, setup_script


_BEAMLINE_UPLOAD_DEFAULTS = {
    # (host, user, data_directory_template) for `dm-upload --reprocess` -
    # confirmed directly from the beamlines' own end-of-experiment scripts
    # (dm_end_user_1id.sh / dm_end_user_20ide.sh). The host is NOT always
    # the same as remote_info_for_beamline's DM-query host: s1's "dm" VM
    # path happens to match (egressy, also used for reads), but s20's
    # dm-upload must run from redwood specifically, not zion (where s20's
    # DM catalog reads are routed) - this is a real, beamline-mandated SOP
    # difference, not an oversight to reconcile away. data_directory_
    # template is filled in with {dserv} (s1c/s20a, from settings.
    # local_bases' basename) and {expid} - distinct from local_root, which
    # is where this tool reads files FROM, not DM's own view of the path.
    "s1": ("egressy", "s1iduser", "/export/{dserv}/{expid}"),
    "s20": ("redwood", "s20iduser", "/net/s20iddata/export/{dserv}/{expid}"),
}


def upload_info_for_experiment(config, beamline, exp_name):
    """(host, user, setup_script, data_directory) to run `dm-upload
    --experiment=<exp_name> --data-directory=<data_directory> --reprocess`
    for exp_name - see _BEAMLINE_UPLOAD_DEFAULTS for why this needs its own
    host routing (settings.upload_hosts) separate from remote_hosts
    (DM-query routing) and checksum_hosts (where hashing runs). Reuses
    settings.setup_scripts - the same DM environment already used for
    catalog reads has dm-upload on its PATH once activated. Returns all
    None if beamline has no configured local_bases entry (dserv can't be
    derived) or no upload default exists for it.
    """
    settings = config.get("settings", {})
    default_host, default_user, template = _BEAMLINE_UPLOAD_DEFAULTS.get(beamline, (None, None, None))
    host = settings.get("upload_hosts", {}).get(beamline, default_host)
    local_base = settings.get("local_bases", {}).get(beamline)
    if not host or not template or not local_base:
        return None, None, None, None
    _, _, setup_script = remote_info_for_beamline(config, beamline)
    dserv = os.path.basename(local_base.rstrip("/"))
    data_directory = template.format(dserv=dserv, expid=exp_name)
    return host, default_user, setup_script, data_directory


def dm_upload_command(exp_name, data_directory):
    """The literal `dm-upload` invocation - a separate function so the GUI
    can show the exact command in a confirmation dialog before running it,
    not just describe it in prose."""
    return f"dm-upload --experiment={shlex.quote(exp_name)} --data-directory={shlex.quote(data_directory)} --reprocess"


def run_dm_upload(host, user, setup_script, exp_name, data_directory, timeout=120):
    """Trigger a DM upload/reprocess for exp_name on host, as user, after
    sourcing setup_script - the same "source <script> && conda activate
    dm-user" environment remote_info_for_beamline's callers already rely
    on to reach DM's Python API also has the dm-upload CLI on PATH.
    """
    inner = f"source {setup_script} && conda activate dm-user && {dm_upload_command(exp_name, data_directory)}"
    return run_shell_command(host, user, "bash -c {}".format(shlex.quote(inner)), timeout=timeout)


def beamline_for_path(local_bases, local_root):
    """Best-effort beamline ("s1"/"s20"/...) for local_root: whichever
    local_bases entry it falls under. None if local_root doesn't fall
    under any configured base (e.g. a manually added experiment outside
    s1c/s20a, or a bare/missing local_bases).

    Checks device+inode identity (os.path.samefile) against each ancestor
    of local_root, not just string-prefix equality after canonical_local_
    root's realpath() - confirmed directly against a real case: the exact
    same underlying storage was reachable through two different real
    mount paths (/home/s20a and /net/s20iddata/export/s20a - same st_dev/
    st_ino, neither a symlink to the other), which realpath() cannot
    unify since there's no symlink chain connecting them, only a shared
    filesystem mounted twice. A user who happened to browse to an
    experiment folder via the path realpath() doesn't happen to produce
    would otherwise silently get no beamline match at all.

    The string comparison still runs first as a fast path (covers the
    overwhelmingly common case - no local_bases entry double-mounted -
    without extra stat() calls); os.path.samefile only kicks in once that
    fails, walking up local_root's ancestors one directory at a time.
    """
    canonical = canonical_local_root(local_root)
    base_canonicals = {beamline: canonical_local_root(base_dir)
                        for beamline, base_dir in local_bases.items() if base_dir}

    for beamline, base_canonical in base_canonicals.items():
        if canonical == base_canonical or canonical.startswith(base_canonical + os.sep):
            return beamline

    ancestor = canonical
    while True:
        for beamline, base_canonical in base_canonicals.items():
            try:
                if os.path.samefile(ancestor, base_canonical):
                    return beamline
            except OSError:
                continue
        parent = os.path.dirname(ancestor)
        if parent == ancestor:
            return None
        ancestor = parent


def beamline_for_local_root(config, local_root):
    """Best-effort beamline ("s1"/"s20"/...) for local_root - see
    beamline_for_path (this is a thin wrapper for callers that already
    have the full config in hand, pulling settings.local_bases out of it -
    the same convention discover_local_experiments's callers rely on)."""
    return beamline_for_path(config.get("settings", {}).get("local_bases", {}), local_root)


def remote_identity_for_beamline(config, beamline):
    """(host, user, remote_base) for where beamline's checksum jobs run and
    where their shared dm_record/ (records + checksum status) lives, from
    settings.checksum_hosts. Distinct from get_upload_status/get_catalog_files's
    routing (settings.remote_hosts/setup_scripts) - that's about reaching
    DM's catalog service (egressy for s1, zion for s20 today); this is
    about where the slow local hashing actually executes (always zion,
    under the beamline's own service account) and where its results are
    shared, regardless of which account launched the GUI.
    """
    entry = config.get("settings", {}).get("checksum_hosts", {}).get(beamline, {})
    return entry.get("host"), entry.get("user"), entry.get("remote_base")


def checksum_records_dir(remote_base):
    return os.path.join(remote_base, "records")


def checksum_status_dir(remote_base):
    return os.path.join(remote_base, "checksum_status")


def checksum_status_path(remote_base, experiment_name):
    return os.path.join(checksum_status_dir(remote_base), f"{experiment_name}.json")


def checksum_unit_name(experiment_name):
    """Deterministic systemd --user unit name for experiment_name's checksum
    job - used both to dedupe (systemctl --user is-active <name>) and to
    launch (systemd-run --user --unit=<name>)."""
    return rj.systemd_unit_name("checksum-verify@.service", experiment_name)


_atomic_write_json = rj.atomic_write_json
write_remote_file = rj.write_remote_file


def save_record_remote(remote_host, remote_user, records_dir, experiment_name, report):
    """Like save_record(), but the actual file write happens on remote_host
    as remote_user via SSH - for callers (Scan, which runs in-process as
    whoever launched the GUI) that aren't already running as the account
    that owns records_dir. Mirrors save_record()'s year-bucketing exactly
    (_exp_records_dirs), so a record's location is identical regardless of
    whether it was written locally (checksum_worker.py, already running as
    the right account) or remotely (Scan).
    """
    exp_records_dir = _exp_records_dirs(records_dir, experiment_name)[0]
    timestamp = int(time.time())
    filepath = os.path.join(exp_records_dir, f"{timestamp}.json")
    write_remote_file(remote_host, remote_user, filepath, json.dumps(report, indent=2))
    return filepath


def launch_checksum_job(host, user, unit_name, job_spec_path, status_path, worker_script_path):
    """Launch checksum_worker.py as a detached systemd --user service on
    host, as user. This is what actually makes the job survive both the
    SSH session that launched it and the GUI process that triggered it -
    requires `loginctl enable-linger` for that account (already enabled
    for s1iduser/s20iduser).
    """
    command = "/usr/bin/python3 {script} --job-spec {spec} --status-file {status}".format(
        script=shlex.quote(worker_script_path),
        spec=shlex.quote(job_spec_path),
        status=shlex.quote(status_path),
    )
    rj.launch_detached_job(
        host, user, unit_name,
        description=f"DM checksum verify: {os.path.basename(job_spec_path)}",
        command=command,
        slice_name="checksum-verify.slice",
    )


lock_dir = rj.lock_dir
acquire_remote_lock = rj.acquire_remote_lock
release_remote_lock = rj.release_remote_lock


def get_upload_status(experiment_name, station_name="SOJOURNER", remote_host=None, remote_user=None,
                       setup_script="/dm/1id/etc/dm.setup.sh", timeout=90):
    """
    Query DM upload status. Returns dict with keys:
    status (str), n_files (int), n_completed (int), n_errors (int),
    upload_complete (bool).

    If remote_host is provided, executes this query on the remote host via
    SSH, sourcing setup_script first - this MUST match the target beamline
    (e.g. ~/bin/dm_setup_20ide.sh for an s20 experiment); the 1-ID default
    only happens to work when querying s1.

    timeout default raised from run_remote_command's own 30s default to
    90s: confirmed directly that DM's listUploadRecords call can be slow
    (or, for at least one specific real experiment, effectively hang) well
    past 30s while every other experiment's identical query returns in
    under a second - 30s was cutting off borderline-slow-but-real
    responses, not just genuinely stuck ones.
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
        return rj.run_remote_command(remote_host, remote_user, setup_cmd, python_code, timeout=timeout)

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
                       setup_script="/dm/1id/etc/dm.setup.sh", timeout=180):
    """
    Fetch DM catalog file metadata.
    Returns dict {experimentFilePath: {"size": fileSize, "md5": md5Sum}}.

    If remote_host is provided, executes this query on the remote host via
    SSH, sourcing setup_script first - see get_upload_status's docstring on
    why this must match the target beamline.

    timeout defaults higher than get_upload_status's (180s vs 90s): this
    call pages through the whole catalog (see the skip/limit loop below),
    so a large experiment's legitimate total query time scales with file
    count in a way a single listUploadRecords lookup never does.
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
        return rj.run_remote_command(remote_host, remote_user, setup_cmd, python_code, timeout=timeout)

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
        if not stat.S_ISDIR(st.st_mode):
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


def _ancestor_dirs(rel_path):
    """Every ancestor directory of rel_path, e.g. 'a/b/c.h5' -> {'a', 'a/b'}
    (not including rel_path itself or the root)."""
    dirs = set()
    parent = os.path.dirname(rel_path)
    while parent:
        dirs.add(parent)
        parent = os.path.dirname(parent)
    return dirs


def diff_directories(comparison):
    """
    Directory-level rollup of compare()'s per-file result: which
    subdirectories exist on one side but have *no* files represented at all
    on the other, derived from the ancestor directories of each path already
    classified by compare() (so this needs no separate directory listing -
    an empty local directory, which contributes no path to comparison at
    all, is correctly never flagged as "missing": there's nothing to have
    landed).

    This is the gap compare()'s per-file MATCH/LOCAL_ONLY/etc. status
    doesn't surface on its own: an entire subdirectory that never got
    uploaded currently only shows up as N separate LOCAL_ONLY files, with
    nothing calling out that they share a parent that's wholly absent from
    Sojourner - easy to miss in a long file list, obvious once named.

    Returns (missing_dirs, extra_dirs) as sorted lists - missing_dirs exist
    locally but have zero presence in the DM catalog; extra_dirs are the
    reverse (present in the catalog, absent locally - e.g. a local copy
    that's since been cleaned up).
    """
    local_dirs = set()
    remote_dirs = set()
    for path, status in comparison.items():
        dirs = _ancestor_dirs(path)
        if status in ("MATCH", "SIZE_MISMATCH", "LOCAL_ONLY"):
            local_dirs |= dirs
        if status in ("MATCH", "SIZE_MISMATCH", "REMOTE_ONLY"):
            remote_dirs |= dirs

    return sorted(local_dirs - remote_dirs), sorted(remote_dirs - local_dirs)


def verify_checksums(local_root, catalog_files, paths, progress_cb=None):
    """
    Explicit checksum verification (MD5) for specific paths.
    Returns dict {path: "CHECKSUM_MATCH" | "CHECKSUM_MISMATCH" |
    "CHECKSUM_UNKNOWN" | "CHECKSUM_ERROR"}.

    progress_cb(path, index, total, status), if given, is called after each
    path is processed (index is 1-based, status is that path's just-computed
    entry in the returned dict) - used by checksum_worker.py to report
    progress and self-throttle between files without this function needing
    to know anything about status files or CPU budgets.
    """
    result = {}
    total = len(paths)

    for index, path in enumerate(paths, start=1):
        if path not in catalog_files:
            result[path] = "CHECKSUM_UNKNOWN"
        else:
            full_path = os.path.join(local_root, path)
            if not os.path.isfile(full_path):
                result[path] = "CHECKSUM_UNKNOWN"
            else:
                # .get("md5", "") only supplies the default when the key is
                # *absent* - DM can return a present "md5Sum": null
                # (checksum not computed yet), which .get() passes through
                # as None verbatim, so this must be checked before calling
                # .lower() on it.
                expected_md5 = catalog_files[path].get("md5")
                if not expected_md5:
                    result[path] = "CHECKSUM_UNKNOWN"
                else:
                    expected_md5 = expected_md5.lower()
                    try:
                        md5_hash = hashlib.md5()
                        with open(full_path, "rb") as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                md5_hash.update(chunk)
                        computed_md5 = md5_hash.hexdigest()
                        result[path] = "CHECKSUM_MATCH" if computed_md5 == expected_md5 else "CHECKSUM_MISMATCH"
                    except (OSError, IOError):
                        result[path] = "CHECKSUM_ERROR"

        if progress_cb:
            progress_cb(path, index, total, result[path])

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

    missing_dirs, extra_dirs = diff_directories(comparison)

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
    elif checksum_mismatch_count > 0:
        # Checked ahead of FULLY_LANDED/PARTIALLY_LANDED deliberately: those
        # are derived only from compare()'s size-based comparison, so a
        # file that size-matched but failed its MD5 (real corruption, or a
        # DM-side re-write) would otherwise still read as "fully landed" -
        # confirmed directly: a synthetic report with one CHECKSUM_MISMATCH
        # among otherwise-MATCHing files came back FULLY_LANDED before this
        # check existed.
        sojourner_status = "CHECKSUM_MISMATCH"
        sojourner_summary = f"{checksum_mismatch_count} file(s) failed checksum verification - possible corruption"
    elif match_count == total_files and remote_only_count == 0:
        sojourner_status = "FULLY_LANDED"
        sojourner_summary = "All local files have landed on Sojourner"
    else:
        sojourner_status = "PARTIALLY_LANDED"
        sojourner_summary = f"Partially landed on Sojourner: {match_count}/{total_files} files match"
        # Worth calling out specifically here (and not in the
        # NOT_ON_SOJOURNER branch above, where *every* local directory is
        # trivially "missing" and saying so would just be noise): this is
        # the case where some files landed and others didn't, so a caller
        # sharing a parent directory with zero presence in the catalog is
        # a real, easy-to-miss structural gap - not just one-off file drops.
        if missing_dirs:
            dirs_shown = ", ".join(missing_dirs[:3]) + ("..." if len(missing_dirs) > 3 else "")
            sojourner_summary += f" ({len(missing_dirs)} whole subdirector{'y' if len(missing_dirs) == 1 else 'ies'} not on Sojourner at all: {dirs_shown})"

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
        "directory_stats": {
            "missing": missing_dirs,
            "extra": extra_dirs,
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


def _print_directory_stats(report):
    """Print missing/extra directories from a report's directory_stats, if
    any - shared by both `check` and `verify-checksums`' CLI output (see
    diff_directories)."""
    dir_stats = report.get("directory_stats", {})
    missing_dirs = dir_stats.get("missing", [])
    extra_dirs = dir_stats.get("extra", [])
    if missing_dirs:
        print(f"Whole subdirectories missing from Sojourner ({len(missing_dirs)}):")
        for d in missing_dirs:
            print(f"  {d}")
    if extra_dirs:
        print(f"Whole subdirectories on Sojourner but not found locally ({len(extra_dirs)}):")
        for d in extra_dirs:
            print(f"  {d}")


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

    # settings has no single top-level "remote_host"/"remote_user" - real
    # configs (see data_integrity_config.json) key these per beamline under
    # "remote_hosts"/"setup_scripts", exactly like the GUI. Route the same
    # way it does: an explicit "beamline" on the experiment entry, or
    # inferred from local_root falling under one of settings.local_bases.
    beamline = exp_config.get("beamline") or beamline_for_local_root(config, local_root)
    remote_host, remote_user, setup_script = remote_info_for_beamline(config, beamline)

    if not remote_host and experimentDaqApi is None:
        sys.exit(
            "dm Python API is not available locally and no remote host could be "
            f"determined for experiment '{args.experiment}' (beamline: {beamline!r}).\n"
            "Either:\n"
            "  1. Source dm.setup.sh and activate dm-user environment\n"
            "  2. Add a 'beamline' key to this experiment's config entry, or set "
            "settings.local_bases so local_root's beamline can be inferred, and "
            "configure settings.remote_hosts/setup_scripts for it\n"
        )

    if args.command == "check":
        upload_status = get_upload_status(args.experiment, station_name, remote_host, remote_user, setup_script)
        catalog_files = get_catalog_files(args.experiment, args.dataset, station_name, remote_host, remote_user, setup_script)
        local_files = scan_local_files(local_root)
        comparison = compare(local_files, catalog_files)

        report = build_report(args.experiment, upload_status, comparison)
        save_record(records_dir, args.experiment, report)

        print(f"Experiment: {args.experiment}")
        print(f"Upload status: {upload_status['status']}")
        print(f"Files: {report['file_stats']['good']} good / {report['file_stats']['bad']} bad")
        print(f"Recommend deletion: {report['recommend_deletion']}")
        _print_directory_stats(report)

    elif args.command == "verify-checksums":
        upload_status = get_upload_status(args.experiment, station_name, remote_host, remote_user, setup_script)
        catalog_files = get_catalog_files(args.experiment, args.dataset, station_name, remote_host, remote_user, setup_script)
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
        _print_directory_stats(report)

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
