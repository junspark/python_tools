# PV Logger

## Overview

A portable replacement for the old `exp_tracking.py` (Python 2, SPEC/APSpy,
hardcoded per-experiment motor/PV list requiring manual comment/uncomment).
Give it one **master list** of every PV ever used across setups; at the
start of each experiment it probes which ones are actually online *right
now* and logs only those — no editing PV definitions per run. If a PV that
was online drops out mid-run, that's logged as `OFFLINE` and (optionally)
emailed as an alert.

Runs as a **persistent, detached job per beamline** (`s1` and `s20` each
have their own master list, host, and job), launched from the GUI but
surviving it being closed — the same architecture `ops/data_integrity`'s
Verify MD5 jobs use. No `pyepics` dependency: PVs are read by shelling out
to the `caget` CLI (facility-wide EPICS Base install) via a bounded thread
pool, one process per PV, since neither beamline host this actually runs on
has a working `pyepics` install.

| File | Purpose |
|---|---|
| `pv_logger.py` | stdlib-only core module + CLI (`list-pvs`, `start`) |
| `pv_logger_gui.py` | PyQt5 GUI; imports `pv_logger.py`, no separate logic |
| `pv_master_list_s1.json` / `pv_master_list_s20.json` | Per-beamline master PV list (name/PV/group) + settings |
| `pv_alert_state.json` | Auto-generated: last-alert time per PV (cooldown) |
| `pv_logger_selection_prefs.json` | Auto-generated: last PV selection per beamline (dialog convenience, gitignored) |

## Setup

Needs PyQt5 (GUI only) in the shared `ops` conda environment
(`../../environment.yml`):

```bash
conda env create -f ../../environment.yml   # or: conda env update -f ../../environment.yml
conda activate ops
```

`caget` itself needs no setup — `settings.caget_path` points at a
facility-wide shared NFS mount
(`/APSshare/epics/base-7.0.10/bin/rhel9-x86_64/caget`), identically present
on every beamline host, no per-account activation required.

## Persistent remote jobs

`pv_logger_gui.py`'s **Start new experiment...** doesn't run discovery or
logging on the GUI's own host — it launches `pv_logger.py start` as a
detached `systemd --user` job on the beamline's own designated host, via
SSH (shared `remote_job.py` primitives, same pattern as Verify MD5):

| Beamline | Host | User |
|---|---|---|
| `s1` | `egressy` | `s1iduser` |
| `s20` | `zion` | `s20iduser` |

This routing (`settings.remote_job` in each master list) is about EPICS
Channel Access reachability, not compute capacity — deliberately different
from `data_integrity`'s checksum-job routing, which runs both beamlines'
jobs on `zion`.

Once launched, the job keeps running detached even if the GUI is closed or
the launching machine reboots — `pv_logger_gui.py` reattaches to it by
polling its status file (`<remote_base>/status/<beamline>.json`, a plain
local read over the shared filesystem, no SSH needed), the same
reattachment mechanism Verify MD5 uses. Only one active logger per beamline
is enforced by an atomic `mkdir`-based lock, checked before launch.
**Stop** requests a clean `systemctl --user stop`, which the job's own
SIGTERM handler turns into a final `STOPPED` status write rather than a
bare kill.

## Master PV list

`pv_master_list_s1.json` / `pv_master_list_s20.json`:

```json
{
  "settings": {
    "log_interval_sec": 5,
    "connect_timeout_sec": 2.0,
    "caget_path": "/APSshare/epics/base-7.0.10/bin/rhel9-x86_64/caget",
    "recipients": ["you@aps.anl.gov"],
    "sender": "pv_logger@your-host.aps.anl.gov",
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "alert_cooldown_min": 60,
    "remote_job": {
      "host": "zion",
      "user": "s20iduser",
      "remote_base": "/home/beams/S20IDUSER/pv_logger"
    }
  },
  "pvs": [
    { "name": "Iring", "pv": "S:SRcurrentAI", "group": "Storage Ring" },
    { "name": "hydraZE", "pv": "1idc:m7.RBV", "group": "GE/Pilatus DETECTOR" }
  ]
}
```

| Setting | Default | Meaning |
|---|---|---|
| `log_interval_sec` | `5` | Seconds between samples once `start` is logging |
| `connect_timeout_sec` | `2.0` | `caget` timeout per PV — PVs are probed in parallel via a bounded thread pool, so total discovery/sample time is bounded by this regardless of how many PVs end up offline, not multiplied by offline count |
| `caget_path` | facility-wide `/APSshare` install | Only needs overriding for a host without that exact mount |
| `recipients` | `[]` | Alert email addresses. Empty = alerts print to console instead of sending |
| `sender` / `smtp_host` / `smtp_port` | — / `apsmail.aps.anl.gov` / `25` | Same relay pattern as `ops/disk_monitor` |
| `alert_cooldown_min` | `60` | Minimum time between repeat alert emails for the same PV while it stays offline |
| `remote_job` | — | `{host, user, remote_base}` for this beamline's persistent job (see above). Missing = Start new experiment refuses to launch |

To add a PV: append `{"name": ..., "pv": ..., "group": ...}` to `pvs`. To
retire one: delete its entry, or just leave it — an unreachable PV is
silently skipped at discovery, no need to comment it out.

### Device categories

The Start-new-experiment checklist groups devices under category headers
(`DEVICE_CATEGORIES` in `pv_logger_gui.py`) — e.g. separate "B/C/D/E Lens
Stacks", "B/C/E Slits"/"White Beam Slits", and "B/C/E Hutch Ion Chambers"
groups, mirroring the hutch/position a device actually belongs to rather
than one generic "Slits" or "Ion Chamber" bucket. A device not mapped to
any category falls into "Other" at the end. To add a new device group,
give its PVs a `"group"` value in the master list and (optionally) add
that name to the relevant category in `DEVICE_CATEGORIES` — an unmapped
group still shows up fine under "Other", categorization is a display
convenience, not a requirement. `DEVICE_CATEGORIES` is shared across both
beamlines' master lists — before removing or renaming an entry, check
both master lists for real members, not just one.

Where a physical device is naturally numbered (e.g. a lens stack with its
own motor per axis), give each unit its own `"group"` like `"C Lens Stack
1"` rather than lumping every unit under one generic device — this is what
lets the checklist show/select one stack at a time instead of all-or-
nothing for a whole hutch's optics. Not every device has this structure:
where the hardware itself has no natural numbering (e.g. s1's B hutch has
five distinct optics — `L1`, `L2`, `RL`, `CRL1`, `CRL2` — with different
axis sets and no shared "stack N" scheme), each unit keeps its own short
name as its `"group"` instead of an invented number.

Within a device group, PVs are ordered by `_pv_sort_key` rather than
raw alphabetical: a name ending in a motion-axis code sorts translation
axes before rotation axes (`X`, `Y`, `Z`, then `RX`, `RY`, `RZ`) — plain
alphabetical order would put every `RX`/`RY`/`RZ` first, since `R` sorts
before `X` in ASCII. Applies to both naming styles in use (`"C Lens1 X"`
and `"D_Lens1X"`). Anything else falls back to plain alphabetical, exactly
as before this existed.

## CLI usage

```bash
# Check what's online without logging anything - good before starting a run
python pv_logger.py list-pvs --config pv_master_list_s20.json

# Start logging - discovers online PVs, writes a CSV, alerts on drops, Ctrl-C to stop
python pv_logger.py start --config pv_master_list_s20.json --outfile ./logs/pokharel_jul26_run1.csv

# Override the sample interval, and print alert emails instead of sending
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --interval 2 --dry-run

# Verify the SMTP relay works end-to-end (force-sends one alert for the first online PV)
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --test-email

# As a detached remote job writes its own live status (used by pv_logger_gui.py, not usually passed by hand)
python pv_logger.py start --config pv_master_list_s20.json --outfile /tmp/t.csv --status-file /tmp/s20.json
```

`start` writes two things next to `--outfile`:
- The CSV itself, with a `Date, name1, name2, ...` header (skipped if the
  file already exists, so re-running `start` against the same `--outfile`
  resumes it) and one row per sample. A PV that's offline for a given
  sample — whether it never came online at discovery, or dropped mid-run —
  is written as the literal string `OFFLINE`.
- `<outfile>.skipped.txt` — every master-list PV that wasn't online at
  discovery time, so it's on record per-experiment what wasn't hooked up.

`--status-file`, if given, gets a live JSON status written after every
sample cycle: `state` (`RUNNING`/`STOPPED`/`FAILED`), `online_count`,
`total_count`, `currently_offline` (every PV currently offline, whether it
dropped mid-run or was never online to begin with), `tracked` (every PV
this job was launched with), `outfile`, `started_at`/`updated_at`, and
`error_message` if `FAILED`. This is how `pv_logger_gui.py` shows live
status for a job without touching EPICS or the CSV file itself.

### Viewing the log

The CSV is a plain wide table (time on rows, one column per PV) — open
directly in Excel, or in Python:

```python
import pandas as pd
df = pd.read_csv("run1.csv", skipinitialspace=True)
df["Date"] = pd.to_datetime(df["Date"])
df.plot(x="Date", y=["hydraZE", "Furnace T1 (C)"])
```

with time on the X axis and any PVs on Y — useful for correlating a failed
scan against motor drift, beam drift, or a temperature excursion.

## GUI usage

```bash
python pv_logger_gui.py --config pv_master_list_s20.json
```

Deliberately **not** a live table of all ~500+ PVs — that's not something
you can usefully watch. Instead:

- A jobs tree shows **both s1 and s20 at once**, each row color-coded
  RUNNING (green) / STOPPED (gray) / FAILED (red), with the discovery
  summary (`N of M PVs online`) and output file in its Details column.
  Expand a beamline's row to see every individually-tracked PV's own
  online/offline state — not just a "currently offline" subset — so a PV
  that's been offline since before logging even started is just as
  visible as one that drops mid-run. A STOPPED/FAILED beamline's PVs are
  shown neutrally (not a false green/red) since only a running job's
  latest sample is trustworthy enough to assert either state.
- A FAILED or STOPPED transition also pops up a message box once, so a
  job that fails immediately (e.g. no PVs online at discovery) isn't
  missed.
- **Start new experiment...** opens a checklist of every device group in
  the master list. Click a group's checkbox to select/deselect all of its
  PVs at once, or click the disclosure triangle next to a group to expand
  it and check/uncheck individual PVs — the group checkbox shows a
  partial/tri-state mark when only some of its PVs are selected. The
  filter box at the top matches PV names and addresses too, not just
  device names, so e.g. typing a signal fragment finds it even if it
  never appears in any device name, and auto-expands any group it matched
  inside.

  Two ways to avoid re-building the same selection every time:
  - The dialog **remembers your last selection per beamline** automatically
    (`pv_logger_selection_prefs.json`) and pre-checks it the next time you
    open the dialog for that beamline. Because this happens automatically,
    a narrow test selection (e.g. checking just one device while testing
    the checklist UI) becomes the default for every subsequent launch
    until explicitly changed — if a launch seems to log far fewer PVs than
    expected, check what's actually selected before assuming a bug.
  - **Load selection from CSV...** reconstructs the *exact* PV selection
    used for any previous run, straight from that run's own logged CSV
    header row — useful for replicating an older experiment's setup rather
    than whatever was picked most recently.
- **Stop** requests a clean shutdown of the beamline's remote job (see
  "Persistent remote jobs" above) — the CSV/skipped-report already written
  stay on disk.
- **Edit recipients...** / **Font size** — same as `ops/disk_monitor`'s GUI.

This GUI is also available as a tab in `../ops_gui.py`, alongside
`ops/disk_monitor`'s GUI, if you'd rather run one combined window. The
underlying widget (`PVLoggerPanel` in `pv_logger_gui.py`) is shared between
the standalone window and that combined GUI - no separate code path.

## History

Originally `pyepics`-based and `s1`-only, built from `exp_tracking.py`'s
`spec.DefineMtr`/`mac.add_logging_PV` calls, `check_device_pvs.sh`'s device
groupings, and a SPEC macro's static `epics_get(...)` calls. Ported to the
`caget`-based, persistent-job, dual-beamline architecture described above
once neither `egressy` nor `zion` turned out to have a working `pyepics`
install or internet access to get one.
