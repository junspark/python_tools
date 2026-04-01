# HRM Background Piezo Monitor & Tweaker

## Overview

Tools to monitor and adjust piezo setpoints in the 20-ID HRM background hutch.

| File | Purpose |
|---|---|
| `hrm_piezo_pvs.txt` | Config: maps EPICS PV names to each piezo section, optional ring-current PV, optional shutter-status PV, and optional foil-wheel RBV PV |
| `run_bkg_hrm_piezo_tweak.py` | CLI tool: `monitor` and `tweak` subcommands |
| `environment.yml` | Conda environment definition |

---

## Setup

### 1. Create the conda environment

```bash
conda env create -f environment.yml
conda activate hrm-monitor
```

Or with pip only:

```bash
pip install pyepics
```

### 2. Verify the config file

`hrm_piezo_pvs.txt` defines two sections (one per piezo), separated by blank lines.
Each line has the form `PV_NAME  %%% COMMENT`:

```
S-DCCT:CurrentM                  %%% STORAGE RING CURRENT PV
S20ID-PSS:FES:BeamBlockingM      %%% FRONT END SHUTTER STATUS
20ida1:m27.RBV                   %%% FOIL WHEEL RBV PV

20aT1:TM:Current3:MeanValue_RBV  %%% PV1 NAME TO MONITOR
20idPI518:PIE518:1:p1_volts      %%% PIEZO1 VOLTAGE PV
20idPI518:PIE518:1:p1_position   %%% PIEZO1 POSITION PV
20idPI518:PIE518:1:p1_sendPOS    %%% PIEZO1 POSITION SETPOINT PV

20aT2:TM:Current1:MeanValue_RBV  %%% PV2 NAME TO MONITOR
20idPI518:PIE518:1:p2_volts      %%% PIEZO2 VOLTAGE PV
20idPI518:PIE518:1:p2_position   %%% PIEZO2 POSITION PV
20idPI518:PIE518:1:p2_sendPOS    %%% PIEZO2 POSITION SETPOINT PV
```

---

## Subcommand: `monitor`

Continuously prints all 8 PVs (4 per piezo) every second until Ctrl-C.

### Optional target argument

| Argument | Description |
|---|---|
| `--target T1,T2` | Target values for Piezo1 and Piezo2 (comma-separated). If omitted, all PVs are displayed with no green/red coloring. |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--interval` | `1.0` | Polling interval in seconds |
| `--ref-current` | off | Reference storage ring current in mA for monitor normalization |
| `--expid` | off | Experiment ID; writes a Markdown session log under `/home/beams/S20IDUSER/new_data/<EXPID>/` |
| `--config` | same dir | Path to PV config file |
| `--dry-run` | off | Use simulated values (no EPICS connection needed) |

Runtime keyboard controls (both subcommands):

- `p`: pause loop activity
- `r`: resume loop activity
- `q`: quit the loop (equivalent to Ctrl-C)

### Color coding

| Color | Meaning |
|---|---|
| Green | Monitor PV is within 5% of its target (fixed) |
| Red | Monitor PV is outside 5% of its target (fixed) |

### Optional storage-ring normalization

If the config file includes a `RING CURRENT PV` entry and you pass `--ref-current`,
monitor values are normalized each cycle as:

```
normalized = raw_monitor_value * (ref_current / ring_current)
```

If `--ref-current` is not provided, or the ring current PV is unavailable, the raw
monitor values are used unchanged.

### Checking phase

After printing the configuration, the script pauses:

```
  Press Enter to start monitoring, or Ctrl-C to abort...
```

Review the targets and tolerance before confirming.

### Use cases

```bash
# Case 1: Raw display — no target set, just watch all 8 PVs (no coloring)
python run_bkg_hrm_piezo_tweak.py monitor

# Case 2: Monitoring with targets — Piezo1 target 100.0, Piezo2 target 80.0
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0

# Case 3: Slower polling interval
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --interval 2.0

# Case 4: Normalize monitor values to a reference SR current
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --ref-current 100

# Case 5: Dry run (no EPICS — uses simulated random-walk values)
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --dry-run

# Case 6: Custom config file
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 \
  --config /path/to/hrm_piezo_pvs.txt

# Case 7: Write a Markdown monitoring record for this experiment
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --expid test123
```

### Example output

```
  Tracking 8 PVs across 2 section(s)
  Interval  : 1.0s
  Piezo1 target : 100  (±5.0%  green = in range / red = out of range)
  Piezo2 target : 80   (±5.0%  green = in range / red = out of range)

  Press Enter to start monitoring, or Ctrl-C to abort...

  Monitoring started. Press Ctrl-C to stop  |  'p' = pause  |  'r' = resume  |  'q' = quit

--- 14:32:01 ---
  [Piezo1]
    monitor  : 20aT1:TM:Current3:MeanValue_RBV            = 98.5      ← green
    voltage  : 20idPI518:PIE518:1:p1_volts                = 45.2
    position : 20idPI518:PIE518:1:p1_position             = 0.231
    setpoint : 20idPI518:PIE518:1:p1_sendPOS              = 0.230

  [Piezo2]
    monitor  : 20aT2:TM:Current1:MeanValue_RBV            = 112.3     ← red
    voltage  : 20idPI518:PIE518:1:p2_volts                = 38.7
    position : 20idPI518:PIE518:1:p2_position             = 0.185
    setpoint : 20idPI518:PIE518:1:p2_sendPOS              = 0.184
```

---

## Subcommand: `tweak`

Runs the same continuous display loop as `monitor`, but when a piezo monitor PV
is out of tolerance it automatically attempts a bounded tweak cycle for that piezo.

### Required arguments

| Argument | Description |
|---|---|
| `--target T1,T2` | Comma-separated targets for Piezo1 and Piezo2 |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--tolerance` | `5.0` | % tolerance: tweak trigger and green/red threshold |
| `--interval` | `1.0` | Display refresh interval in seconds |
| `--ref-current` | off | Reference storage ring current in mA for monitor normalization |
| `--pos-range` | `0.1` | Allowed drive range = current position ± `pos-range` for each piezo |
| `--max-steps` | `5` | Max tweak steps per cycle for each piezo |
| `--settle-time` | `3.0` | Seconds to wait after each caput before reading PV values |
| `--confirm` | off | Prompt for user approval before each caput |
| `--expid` | off | Experiment ID; writes a Markdown tweak/monitor record under `/home/beams/S20IDUSER/new_data/<EXPID>/` |
| `--config` | same dir | Path to PV config file |
| `--dry-run` | off | Use simulated values (no EPICS connection needed) |

### Drive position limits (`--pos-range`)

These guard rails prevent the piezo from being driven beyond a safe range.

- On every tweak run, the script reads the current position PV for each piezo.
- It then computes an allowed range from `--pos-range`:
  ```
  pos_min = current_position - pos_range
  pos_max = current_position + pos_range
  ```

These computed ranges are shown before the loop starts so you can verify them before enabling tweaks.

If you pause (`p`) and later resume (`r`) in `tweak` mode, the tool re-reads each
piezo position PV and refreshes `pos_min` / `pos_max` from the current position
and `--pos-range` before continuing.

### Automatic tweak skip conditions

Even in `tweak` mode, the script will skip the write phase for a cycle when any of these conditions is true:

- Storage ring current is more than 10% below `--ref-current`
- Front end shutter status indicates the beam is blocked
- Foil wheel RBV is not equal to `1` (i.e. the foil wheel is not in the correct position)

In those cases, the tool continues monitoring and logging, but does not issue any `caput` writes for that cycle.

The `FOIL WHEEL RBV PV` entry in the config is optional. If it is absent, the foil-wheel check is skipped and tweaking proceeds regardless of foil position.

### Session logging (`--expid`)

If `--expid NAME` is provided, the tool appends a Markdown session record to:

```text
/home/beams/S20IDUSER/new_data/NAME/hrm_auto_tweak_record.md
```

The log includes:

- start time and mode (`monitor` or `tweak`)
- configured targets and optional reference current
- per-cycle PV snapshots
- tweak attempts, step decisions, guard-rail hits, and stop events

### Checking phase

Before the loop starts, the script prints the tweak settings and pauses:

```
  Tracking 8 PVs across 2 section(s)
  Interval  : 1.0s
  SR current PV  : S-DCCT:CurrentM
  Ref current    : 100 mA  (monitor values normalized to this)
  Piezo1 target : 10300  (±5.0%  green / red)
  Piezo2 target : 6500   (±5.0%  green / red)

  Tweak mode ON
  Settle time : 3.0s
  Step size   : 0.01
  Max steps   : 5 per cycle
  Confirm     : OFF
  Piezo1 pos range : [0.150000, 0.350000]  (auto)
  Piezo2 pos range : [0.120000, 0.320000]  (auto)

  Press Enter to start tweaking, or Ctrl-C to abort...
```

Once running, you can pause or resume without terminating the process:

```
  Started. Press Ctrl-C to stop  |  'p' = pause  |  'r' = resume  |  'q' = quit
```

The same `p/r/q` reminder line is printed again during the loop so controls remain visible.
The reminder is color-highlighted (green) in the terminal for visibility during long runs.

### Color coding during tweak

| Color | Meaning |
|---|---|
| Bold yellow | Tweak mode header and per-piezo position ranges |
| Cyan | Probe step and direction decision |
| Yellow | Each active step being written to the setpoint |
| Bold green | Target reached successfully |
| Red | Safety stop: position range exceeded, error not improving, or max steps reached |

### Tweak algorithm

1. **Display pass** — print all PVs for both piezos with green/red target coloring.
  - If `--ref-current` is enabled, compare against per-cycle normalized targets.
2. **Out-of-range detection** — identify any piezo whose monitor PV is outside tolerance.
  - If SR current is too low or the front end shutter is blocking beam, skip tweaking for that cycle.
3. **Probe step** — for each out-of-range piezo, try a `+0.01` step first; if that is outside the allowed range, try `-0.01`.
4. **Direction choice** — continue in the direction that improves the monitor error.
5. **Bounded stepping** — keep stepping until one of these occurs:
   - Monitor PV reaches tolerance ✓
  - Error stops improving: step back to the best position seen in this cycle,
    then stop if still out of tolerance ✗
   - Next position would exceed the computed position range ✗
   - `--max-steps` is exhausted ✗
6. **Resume monitoring** — after each tweak cycle, return to the continuous display loop.

### Use cases

```bash
# Case 1: Enable auto-tweak monitoring for both piezos
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500

# Case 2: Slower display refresh
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --interval 2.0

# Case 2b: During a run, press 'p' to pause and 'r' to resume

# Case 3: Normalize against storage ring current
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --ref-current 100

# Case 4: Allow a wider tweak envelope around current positions
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --pos-range 0.2

# Case 5: Tighter tolerance before a piezo is considered in-range
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --tolerance 2.0

# Case 6: Limit how many correction steps happen per cycle
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --max-steps 3

# Case 7: Test behavior without EPICS hardware
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --dry-run

# Case 8: Require manual confirmation before each caput
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --confirm

# Case 9: Write a persistent tweak log for an experiment
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --expid test123
```

---

## Typical Workflow

```bash
# Step 1: Confirm PVs are live and check baseline values
python run_bkg_hrm_piezo_tweak.py monitor --target 10300,6500

# Step 2: Turn on auto-tweak mode with bounded correction steps
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500

# Step 3: If needed, widen allowed position range or increase max steps
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --pos-range 0.2 --max-steps 8

# Step 4: Return to display-only monitoring
python run_bkg_hrm_piezo_tweak.py monitor --target 10300,6500
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `pyepics not installed` | Package missing | `pip install pyepics` or use `--dry-run` |
| `SR current PV found in config but --ref-current not given` | Normalization was available but not enabled | Pass `--ref-current <mA>` if you want SR-current normalization |
| `SR current (...) is >10% below ref (...) — tweak skipped` | Beam current too low for reliable comparison | Wait for current recovery or lower `--ref-current` |
| `Front end shutter is ON (beam blocked) — tweak skipped` | Beam is blocked at the front end | Re-open beam path before expecting auto-tweak writes |
| `foil wheel not in position (RBV=...) — tweak skipped` | Foil wheel RBV PV value is not `1` | Verify foil wheel position and wait for it to reach the correct position |
| `Cannot read monitor PV` | EPICS disconnected or wrong PV name | Check network / config file |
| `Config file not found` | Wrong path | Use `--config /full/path/to/file` |
| `Section N not found` | Fewer sections than requested | Check blank-line-separated blocks in config |
| `cannot step in either direction within [...]` | Position range too tight for the fixed step size | Increase `--pos-range` |
| `position [...] outside [...]` | Next step would leave the allowed range | Increase `--pos-range` |
| `max steps (...) reached` | Target was not reached within one tweak cycle | Increase `--max-steps` or let additional cycles run |
| `error not improving` | Plateau — target may be unreachable or step direction saturated | Check target value or widen `--pos-range` |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Normal process exit |
| `1` | Startup/config/EPICS input error |
