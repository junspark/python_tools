# PV Logger

## Overview

A portable replacement for the old `exp_tracking.py` (Python 2, SPEC/APSpy,
hardcoded per-experiment motor/PV list requiring manual comment/uncomment).
Give it one **master list** of every PV ever used across setups; at the
start of each experiment it probes which ones are actually online *right
now* and logs only those — no editing PV definitions per run. If a PV that
was online drops out mid-run, that's logged as `OFFLINE` and (optionally)
emailed as an alert.

| File | Purpose |
|---|---|
| `pv_logger.py` | `pyepics` + stdlib-only core module + CLI (`list-pvs`, `start`) |
| `pv_logger_gui.py` | PyQt5 GUI; imports `pv_logger.py`, no separate logic |
| `pv_master_list.json` | Master PV list (name/PV/group) + settings |
| `pv_alert_state.json` | Auto-generated: last-alert time per PV (cooldown) |

No dependency on APSpy or any beamline-specific import path — `epics.PV`
directly, so this runs the same way on any host with network access to the
relevant IOCs.

## Setup

Needs `pyepics` (core) and PyQt5 (GUI only), both in the shared `ops` conda
environment (`../../environment.yml`):

```bash
conda env create -f ../../environment.yml   # or: conda env update -f ../../environment.yml
conda activate ops
```

## Master PV list

`pv_master_list.json`:

```json
{
  "settings": {
    "log_interval_sec": 5,
    "connect_timeout_sec": 2.0,
    "recipients": ["you@aps.anl.gov"],
    "sender": "pv_logger@your-host.aps.anl.gov",
    "smtp_host": "apsmail.aps.anl.gov",
    "smtp_port": 25,
    "alert_cooldown_min": 60
  },
  "pvs": [
    { "name": "Iring", "pv": "S:SRcurrentAI", "group": "Storage ring" },
    { "name": "hydraZE", "pv": "1idc:m7.RBV", "group": "GE/Pilatus DETECTOR" }
  ]
}
```

| Setting | Default | Meaning |
|---|---|---|
| `log_interval_sec` | `5` | Seconds between samples once `start` is logging |
| `connect_timeout_sec` | `2.0` | How long discovery waits for the whole master list to connect (not per-PV — see below) |
| `recipients` | `[]` | Alert email addresses. Empty = alerts print to console instead of sending |
| `sender` / `smtp_host` / `smtp_port` | — / `apsmail.aps.anl.gov` / `25` | Same relay pattern as `ops/disk_monitor` |
| `alert_cooldown_min` | `60` | Minimum time between repeat alert emails for the same PV while it stays offline |

To add a PV: append `{"name": ..., "pv": ..., "group": ...}` to `pvs`. To
retire one: delete its entry, or just leave it — an unreachable PV is
silently skipped at discovery, no need to comment it out.

**Provenance of the shipped `s1` list** (559 entries): mechanically pulled
from `ops/exp_tracking.py` (every `spec.DefineMtr`/`mac.add_logging_PV`
call, including ones inside commented-out blocks — translated motor names
to `<base PV>.RBV`), `check_device_pvs.sh`'s detector/shutter/slit tables,
and the net-new static PVs in `write_parfile_general.mac` (dynamic,
`sprintf`-templated PV names there were skipped — those need to be added by
hand if you want them). Names that collided across different physical PVs
(e.g. two different scaler banks both labeled `IC-C1` in the old script)
were disambiguated with their IOC prefix, e.g. `IC-C1 (1id)` / `IC-C1
(1ide2)`. A separate `s20`-hutch list is a planned follow-up, not included
yet.

Because discovery probes all PVs in parallel and then polls once, total
discovery time is bounded by `connect_timeout_sec` regardless of how many
end up offline (not `connect_timeout_sec * offline_count`) — safe to run
against a master list far larger than what's actually connected for a
given experiment.

## CLI usage

```bash
# Check what's online without logging anything - good before starting a run
python pv_logger.py list-pvs --config pv_master_list.json

# Start logging - discovers online PVs, writes a CSV, alerts on drops, Ctrl-C to stop
python pv_logger.py start --config pv_master_list.json --outfile ./logs/pokharel_jul26_run1.csv

# Override the sample interval, and print alert emails instead of sending
python pv_logger.py start --config pv_master_list.json --outfile /tmp/t.csv --interval 2 --dry-run

# Verify the SMTP relay works end-to-end (force-sends one alert for the first online PV)
python pv_logger.py start --config pv_master_list.json --outfile /tmp/t.csv --test-email
```

`start` writes two things next to `--outfile`:
- The CSV itself, with a `Date, name1, name2, ...` header (skipped if the
  file already exists, so re-running `start` against the same `--outfile`
  resumes it) and one row per sample. A PV that's offline for a given
  sample — whether it never came online at discovery, or dropped mid-run —
  is written as the literal string `OFFLINE`.
- `<outfile>.skipped.txt` — every master-list PV that wasn't online at
  discovery time, so it's on record per-experiment what wasn't hooked up.

There's no cron entry for this one (unlike `ops/disk_monitor`) — it's a
per-experiment interactive tool you start and stop around a run, not a
background daemon.

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
python pv_logger_gui.py --config pv_master_list.json
```

Deliberately **not** a live table of all ~500+ PVs — that's not something
you can usefully watch. Instead:

- **Start new experiment...** — pick an output CSV, runs discovery, and
  starts logging. This is also how you restart monitoring for a new
  experiment.
- **Stop** — stops the logging timer (the CSV/skipped-report already
  written stay on disk).
- Status panel shows RUNNING/STOPPED, start time, output file, and the
  discovery summary (`N of M PVs online`).
- The table below only ever lists **currently-offline** PVs — empty when
  everything's fine, populated live as things drop, which is the actual
  signal worth watching.
- **Edit recipients...** / **Font size** — same as `ops/disk_monitor`'s GUI.

This GUI is also available as a tab in `../ops_gui.py`, alongside
`ops/disk_monitor`'s GUI, if you'd rather run one combined window. The
underlying widget (`PVLoggerPanel` in `pv_logger_gui.py`) is shared between
the standalone window and that combined GUI - no separate code path.
