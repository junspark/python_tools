# HRM Background Piezo Monitor & Tweaker

## Overview

Tools to monitor and adjust piezo setpoints in the 20-ID HRM background hutch.

| File | Purpose |
|---|---|
| `bkg_hrm_piezo_tweak.py` | Config: maps EPICS PV names to each piezo section |
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

`bkg_hrm_piezo_tweak.py` defines two sections (one per piezo), separated by blank lines.
Each line has the form `PV_NAME  %%% COMMENT`:

```
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

### Required argument

| Argument | Description |
|---|---|
| `--target T1,T2` | Target values for Piezo1 and Piezo2 (comma-separated, **required**) |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--interval` | `1.0` | Polling interval in seconds |
| `--tolerance` | `5.0` | % tolerance around target for green/red coloring |
| `--config` | same dir | Path to PV config file |
| `--dry-run` | off | Use simulated values (no EPICS connection needed) |

### Color coding

| Color | Meaning |
|---|---|
| Green | Monitor PV is within `--tolerance` % of its target |
| Red | Monitor PV is outside tolerance |

### Checking phase

After printing the configuration, the script pauses:

```
  Press Enter to start monitoring, or Ctrl-C to abort...
```

Review the targets and tolerance before confirming.

### Use cases

```bash
# Case 1: Basic monitoring — Piezo1 target 100.0, Piezo2 target 80.0
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0

# Case 2: Slower polling interval
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --interval 2.0

# Case 3: Tighter tolerance (2% instead of default 5%)
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --tolerance 2.0

# Case 4: Dry run (no EPICS — uses simulated random-walk values)
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 --dry-run

# Case 5: Custom config file
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0 \
    --config /path/to/bkg_hrm_piezo_tweak.py
```

### Example output

```
  Tracking 8 PVs across 2 section(s)
  Interval  : 1.0s
  Piezo1 target : 100  (±5.0%  green = in range / red = out of range)
  Piezo2 target : 80   (±5.0%  green = in range / red = out of range)

  Press Enter to start monitoring, or Ctrl-C to abort...

  Monitoring started. Press Ctrl-C to stop.

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
| `--tolerance` | `5.0` | Acceptable error as % of target |
| `--interval` | `1.0` | Display refresh interval in seconds |
| `--pos-range` | `0.1` | Allowed drive range = current position ± `pos-range` for each piezo |
| `--max-steps` | `5` | Max tweak steps per cycle for each piezo |
| `--confirm` | off | Prompt for user approval before each caput |
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

### Checking phase

Before the loop starts, the script prints the tweak settings and pauses:

```
  Tracking 8 PVs across 2 section(s)
  Interval  : 1.0s
  Piezo1 target : 10300  (±5.0%  green / red)
  Piezo2 target : 6500   (±5.0%  green / red)

  Tweak mode ON
  Settle time : 1.0s (fixed)
  Step size   : 0.01
  Max steps   : 5 per cycle
  Piezo1 pos range : [0.150000, 0.350000]  (auto)
  Piezo2 pos range : [0.120000, 0.320000]  (auto)

  Press Enter to start tweaking, or Ctrl-C to abort...
```

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
2. **Out-of-range detection** — identify any piezo whose monitor PV is outside tolerance.
3. **Probe step** — for each out-of-range piezo, try a `+0.01` step first; if that is outside the allowed range, try `-0.01`.
4. **Direction choice** — continue in the direction that improves the monitor error.
5. **Bounded stepping** — keep stepping until one of these occurs:
   - Monitor PV reaches tolerance ✓
   - Error stops improving ✗
   - Next position would exceed the computed position range ✗
   - `--max-steps` is exhausted ✗
6. **Resume monitoring** — after each tweak cycle, return to the continuous display loop.

### Use cases

```bash
# Case 1: Enable auto-tweak monitoring for both piezos
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500

# Case 2: Slower display refresh
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --interval 2.0

# Case 3: Allow a wider tweak envelope around current positions
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --pos-range 0.2

# Case 4: Tighter tolerance before a piezo is considered in-range
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --tolerance 2.0

# Case 5: Limit how many correction steps happen per cycle
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --max-steps 3

# Case 6: Test behavior without EPICS hardware
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --dry-run

# Case 7: Require manual confirmation before each caput
python run_bkg_hrm_piezo_tweak.py tweak --target 10300,6500 --confirm
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
