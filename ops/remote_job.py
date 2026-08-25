#!/usr/bin/env python3
"""
Generic, tool-agnostic primitives for running detached jobs on a remote host
via SSH + systemd --user: atomic mkdir-based locks, atomic remote/local file
writes, and a systemd-run launcher. Originally written for dm_integrity.py's
persistent Verify MD5 checksum jobs; extracted here so pv_logger.py's
persistent PV-logging jobs can reuse the same, already-hardened SSH/locking
plumbing instead of a second copy of it.

Nothing here is DM- or PV-logger-specific - no imports from either tool.
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path


def _ssh_argv(remote_spec):
    """Common ssh argv prefix for every remote call in this module: reuse a
    persistent control connection per (user, host, port) via OpenSSH's
    ControlMaster, so a sequence of calls against the same remote_spec (a
    lock acquire, a file write, a launch, all in one action) pay for one SSH
    handshake instead of one each. ControlPersist keeps the master open for
    a while after the last client exits so back-to-back unrelated actions
    benefit too. Falls back to a plain new connection if the control socket
    can't be created (e.g. no ~/.ssh) - ControlMaster=auto degrades
    gracefully rather than erroring.
    """
    return [
        "ssh",
        "-o", "ConnectTimeout=10",
        "-o", "ControlMaster=auto",
        "-o", "ControlPath=~/.ssh/cm-%r@%h:%p",
        "-o", "ControlPersist=300",
        remote_spec,
    ]


def run_remote_command(host, user, setup_cmd, python_code, timeout=30):
    """Run python_code on host (after sourcing setup_cmd) via SSH, returning
    its stdout parsed as JSON.

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
    remote_spec = f"{user}@{host}" if user else host
    remote_cmd = "bash -c {}".format(shlex.quote(setup_cmd + " && python3 -"))

    try:
        result = subprocess.run(
            _ssh_argv(remote_spec) + [remote_cmd],
            input=python_code,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Remote command failed: {result.stderr}")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        # Distinguished from the generic "SSH execution failed" below: SSH
        # itself connected fine here (a timeout means the *remote* python
        # process didn't finish in time, not that the connection couldn't
        # be established) - conflating the two as one generic message reads
        # like a network/auth problem when it's actually the remote call
        # (e.g. a DM API query) itself being slow or stuck. Confirmed
        # directly against a real, reproducible case: one specific
        # experiment's DM upload-status query hung past this timeout on
        # every attempt while every other experiment's identical query
        # returned in well under a second - a server-side condition on
        # that experiment, not anything wrong with the SSH/env setup here.
        # That specific case turned out to be an already-archived
        # experiment (confirmed via DM Station's Experiments tab) - called
        # out explicitly here since it's easy to forget an experiment's
        # archive status between sessions, unlike dm-upload's own "already
        # archived" error (see dm_integrity_gui.py's _on_upload_error),
        # Scan/Verify MD5's DM queries have no equivalent fast check to
        # surface it any earlier than this timeout.
        raise RuntimeError(
            f"Remote command on {remote_spec} timed out after {timeout}s - the SSH connection "
            "itself succeeded, but the remote command didn't finish in time (e.g. a slow or "
            "stuck DM API call). Retrying with a longer timeout may help; if it times out "
            "consistently for the same experiment, the hang is most likely on DM's end for "
            "that specific experiment (e.g. it may already be archived - check DM Station's "
            "Experiments/Uploads tabs), not in this tool.")
    except json.JSONDecodeError:
        raise RuntimeError(f"Remote command returned invalid JSON: {result.stdout}")
    except Exception as e:
        raise RuntimeError(f"SSH execution failed: {e}")


def canonical_path(path):
    """Resolve a (possibly ~-relative, possibly symlinked) local path to its
    canonical absolute form. E.g. '~/mnt/s1c/<expid>' resolves to the same
    '/home/s1c/<expid>' regardless of whether it's expanded as parkjs,
    S1IDUSER, or S20IDUSER - confirmed directly. This is what makes a path
    chosen by whoever launched a GUI still valid once embedded in a job spec
    or command that runs remotely under a different account: canonicalize
    before it's written into a job spec or any remote command, never pass
    the launching user's own ~-relative or home-prefixed form through.
    """
    return os.path.realpath(os.path.expanduser(path))


def atomic_write_json(path, data):
    """Write JSON atomically (tmp file + os.replace) so a concurrent reader
    (a GUI's poll timer, or a peer job counting active workers for a CPU
    governor) never sees a partially-written file."""
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def write_remote_file(host, user, path, content, timeout=30):
    """Write content (a string) to path on host as user, via SSH - for
    anything that needs to land under a shared remote directory from a
    process that isn't already running as that account.
    """
    remote_spec = f"{user}@{host}" if user else host
    # See run_remote_command's docstring for why this must travel as one
    # already shell-quoted string, not separate argv elements: ssh joins
    # trailing argv with spaces before handing it to the remote shell.
    remote_cmd = "bash -c {}".format(shlex.quote(
        "mkdir -p {} && cat > {}".format(shlex.quote(os.path.dirname(path)), shlex.quote(path))
    ))

    result = subprocess.run(
        _ssh_argv(remote_spec) + [remote_cmd],
        input=content,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Remote write to {path} failed: {result.stderr}")


def run_shell_command(host, user, command, timeout=15):
    """Run a plain shell command string on host as user via SSH - for
    one-off actions (e.g. `systemctl --user stop <unit>`) that don't fit
    run_remote_command's python-code-over-stdin shape. Raises on nonzero
    exit; returns the completed process (stdout/stderr) on success.
    """
    remote_spec = f"{user}@{host}" if user else host
    result = subprocess.run(
        _ssh_argv(remote_spec) + [command],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        # Include stdout as well as stderr: CLI tools commonly print their
        # actual failure reason (a traceback, a "no such experiment"
        # message) to stdout rather than stderr, and a caller here has no
        # other way to see it - confirmed directly, an earlier version that
        # only surfaced stderr showed a bare "Remote command failed: " with
        # nothing after it for a dm-upload failure whose real error was on
        # stdout, indistinguishable from every other failure mode.
        detail = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        raise RuntimeError(f"Remote command failed (exit {result.returncode}): {detail}")
    return result


def lock_dir(remote_base, kind, key):
    """Path to a per-key, per-operation lock directory under a shared remote
    base - e.g. .../locks/checksum__pokharel_jul26 or .../locks/pvlogger__s1.
    kind namespaces independent operations that shouldn't conflict with each
    other (e.g. a Scan and a Verify MD5 for the same experiment); key is
    whatever needs its own single-instance guarantee (an experiment name, a
    beamline name, ...)."""
    return os.path.join(remote_base, "locks", f"{kind}__{key}")


def acquire_remote_lock(host, user, path, timeout=15):
    """Atomically acquire a lock via `mkdir` on host as user - mkdir either
    creates the directory or fails with a nonzero exit if it already
    exists, with no race window, unlike a check-then-write-status-file
    approach. Returns True if acquired, False if someone else already
    holds it (a live process crashing without releasing is a known,
    accepted risk of this simple scheme - not addressed here, matching this
    project's "assume good-faith interactive use" posture rather than
    adding lock-staleness/timeout recovery logic).
    """
    remote_spec = f"{user}@{host}" if user else host
    remote_cmd = "bash -c {}".format(shlex.quote(
        "mkdir -p {} && mkdir {}".format(shlex.quote(os.path.dirname(path)), shlex.quote(path))
    ))
    result = subprocess.run(
        _ssh_argv(remote_spec) + [remote_cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode == 0


def release_remote_lock(host, user, path, timeout=15):
    remote_spec = f"{user}@{host}" if user else host
    remote_cmd = "bash -c {}".format(shlex.quote(f"rmdir {shlex.quote(path)}"))
    subprocess.run(_ssh_argv(remote_spec) + [remote_cmd], capture_output=True, text=True, timeout=timeout)


def systemd_unit_name(template, key):
    """Deterministic systemd --user unit name for key, from a template like
    "checksum-verify@.service" or "pv-logger@.service" - used both to
    dedupe (systemctl --user is-active <name>) and to launch (systemd-run
    --user --unit=<name>). systemd-escape --template handles arbitrary key
    characters (hyphens, etc.) safely and reversibly; falls back to a
    simple manual sanitize if systemd-escape isn't on PATH (e.g. running
    tests on a host without systemd)."""
    try:
        result = subprocess.run(
            ["systemd-escape", f"--template={template}", key],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        prefix, suffix = template.split("@", 1)
        return f"{prefix}@{sanitized}{suffix}"


def launch_detached_job(host, user, unit_name, description, command, slice_name=None, timeout=15):
    """Launch command as a detached systemd --user service on host, as
    user. This is what actually makes a job survive both the SSH session
    that launched it and the GUI process that triggered it - requires
    `loginctl enable-linger` for that account. --unit (a persistent
    service, not --scope) keeps the job fully detached from this SSH
    session's own process tree; --collect ensures a finished/failed unit is
    garbage-collected automatically rather than lingering and blocking a
    future launch under the same deterministic unit name (a real bug hit
    and fixed in this project's checksum-job feature: a killed job's
    "failed" unit stuck around and every subsequent launch attempt failed
    with "Unit ... was already loaded or has a fragment file" until
    `systemctl --user reset-failed` was run manually).
    """
    remote_spec = f"{user}@{host}" if user else host
    slice_arg = f"--slice={slice_name} " if slice_name else ""
    remote_cmd = (
        "systemd-run --user --unit={unit} --collect {slice}"
        "--description={desc} -- {command}"
    ).format(
        unit=shlex.quote(unit_name),
        slice=slice_arg,
        desc=shlex.quote(description),
        command=command,
    )
    result = subprocess.run(
        _ssh_argv(remote_spec) + [remote_cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to launch job: {result.stderr}")
