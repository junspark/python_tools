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

Adjusts the setpoint of one piezo to bring its monitor PV within tolerance of a target.

### Required arguments

| Argument | Description |
|---|---|
| `--target T` | Target value for the monitor PV |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--section` | `1` | Piezo section to tweak: `1` or `2` |
| `--step` | `0.01` | Setpoint step size per iteration |
| `--max-change` | `0.05` | Max cumulative absolute displacement from start position |
| `--tolerance` | `5.0` | Acceptable error as % of target |
| `--settle` | `0.5` | Seconds to wait after each step |
| `--pos-min P1,P2` | auto | Min allowed drive position for Piezo1,Piezo2 (comma-separated) |
| `--pos-max P1,P2` | auto | Max allowed drive position for Piezo1,Piezo2 (comma-separated) |
| `--config` | same dir | Path to PV config file |

### Drive position limits (`--pos-min` / `--pos-max`)

These guard rails prevent the piezo from being driven beyond a safe range.

- **If provided:** the script uses the value for the selected section (e.g. `--section 1` uses the first of the two comma-separated values).
- **If omitted:** the script reads the current position PV and automatically sets:
  ```
  pos_min = current_position - 0.1
  pos_max = current_position + 0.1
  ```

Both limits are always displayed during the checking phase (bold yellow) so you can verify them before tweaking begins.

### Checking phase

Before any PV is written, the script prints a full parameter summary and pauses:

```
  Monitor PV  : 20aT1:TM:Current3:MeanValue_RBV
  Setpoint PV : 20idPI518:PIE518:1:p1_sendPOS
  Current     : 98.5
  Target      : 100.0
  Tolerance   : 5.0%
  Max change  : 0.0500
  Step        : 0.0100
  Settle time : 0.5s
  Pos min     : 0.150000  (auto: current ±0.1)
  Pos max     : 0.350000  (auto: current ±0.1)

  Press Enter to start tweaking, or Ctrl-C to abort...
```

### Color coding during tweak

| Color | Meaning |
|---|---|
| Bold yellow | "TWEAKING IN PROGRESS" banner |
| Cyan | Probe step and direction decision |
| Yellow | Each active step being written to the setpoint |
| Bold green | Target reached successfully |
| Red | Safety stop (pos limit, max-change) or error no longer improving |

### Tweak algorithm

1. **Tolerance check** — if already within tolerance, exit immediately (no PV writes).
2. **Probe step** — move setpoint +0.01 and read monitor PV.
   - If monitor moves closer to target → continue in `+` direction.
   - If monitor moves further → undo step, continue in `−` direction.
3. **Iterative stepping** — keep stepping in the chosen direction until:
   - Monitor PV is within tolerance of target ✓
   - Error stops decreasing (plateau) ✗
   - Cumulative displacement exceeds `--max-change` ✗
   - Next position would exceed `pos-min` / `pos-max` ✗
4. **Summary** — prints final position, monitor value, and error %.

### Use cases

```bash
# Case 1: Tweak Piezo1 to target 100.0 (pos limits auto-set from current position)
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0

# Case 2: Tweak Piezo2 to target 80.0
python run_bkg_hrm_piezo_tweak.py tweak --section 2 --target 80.0

# Case 3: Explicit drive position limits for both piezos (uses Piezo1 limits for section 1)
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0 \
    --pos-min -0.5,-0.5 --pos-max 0.5,0.5

# Case 4: Finer steps with tighter tolerance
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0 \
    --step 0.005 --tolerance 2.0

# Case 5: Larger allowed range and longer settle time
python run_bkg_hrm_piezo_tweak.py tweak --section 2 --target 80.0 \
    --max-change 0.1 --settle 1.0

# Case 6: Allow more displacement with explicit safe limits
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0 \
    --max-change 0.05 --pos-min 0.1,0.1 --pos-max 0.4,0.4
```

---

## Typical Workflow

```bash
# Step 1: Confirm PVs are live and check baseline values
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0

# Step 2: If Piezo1 is off, tweak it (pos limits auto-set)
python run_bkg_hrm_piezo_tweak.py tweak --section 1 --target 100.0

# Step 3: If Piezo2 is off, tweak it
python run_bkg_hrm_piezo_tweak.py tweak --section 2 --target 80.0

# Step 4: Confirm both are back in range
python run_bkg_hrm_piezo_tweak.py monitor --target 100.0,80.0
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `pyepics not installed` | Package missing | `pip install pyepics` or use `--dry-run` |
| `Cannot read monitor PV` | EPICS disconnected or wrong PV name | Check network / config file |
| `Config file not found` | Wrong path | Use `--config /full/path/to/file` |
| `Section N not found` | Fewer sections than requested | Check blank-line-separated blocks in config |
| `Probe position outside allowed range` | Auto pos limit too tight | Provide explicit `--pos-min` / `--pos-max` |
| `Max change reached` | Target unreachable within `--max-change` | Increase `--max-change` or check target value |
| `Error no longer decreasing` | Plateau — target may be unreachable | Try different `--step` or `--settle` time |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success (tweak reached target, or monitor exited cleanly) |
| `1` | Failure (target not reached, config error, or safety stop) |
