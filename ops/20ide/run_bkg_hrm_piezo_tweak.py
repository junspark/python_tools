#!/usr/bin/env python3
"""
HRM Background Piezo Monitor & Tweaker

Reads PV names from bkg_hrm_piezo_tweak.py.

Both subcommands run the same continuous display loop (all 8 PVs, green/red
coloring against per-piezo targets).  The only difference is that 'tweak'
automatically adjusts setpoints when a piezo monitor is out of tolerance.

Subcommands
-----------
monitor   Display-only loop.  No PVs are ever written.
tweak     Same display loop, but auto-adjusts setpoints when out of tolerance.

Shared arguments (both subcommands)
------------------------------------
  --target   T1,T2    Per-piezo target values (required)
  --tolerance %       Green/red threshold and tweak trigger  (default 5 %)
  --interval  s       Display refresh interval               (default 1 s)
  --config    path    PV config file
  --dry-run           Simulate PV values without EPICS

Tweak-only additional arguments
--------------------------------
  --pos-range  R      Allowed drive range = current_pos ± R  (default 0.1)
  --max-steps  N      Max setpoint steps per tweak cycle     (default 5)
  --confirm           Prompt for approval before each caput  (default off)
  (settle time is fixed at 1 s)

Usage examples
--------------
  python run_bkg_hrm_piezo_tweak.py monitor --target 10300,6500
  python run_bkg_hrm_piezo_tweak.py monitor --target 10300,6500 --interval 2
  python run_bkg_hrm_piezo_tweak.py tweak   --target 10300,6500
  python run_bkg_hrm_piezo_tweak.py tweak   --target 10300,6500 --pos-range 0.2
  python run_bkg_hrm_piezo_tweak.py tweak   --target 10300,6500 --max-steps 3
"""

import argparse
import os
import random
import sys
import time

try:
    import epics
    _EPICS_AVAILABLE = True
except ImportError:
    _EPICS_AVAILABLE = False

# ---------------------------------------------------------------------------
# EPICS / dry-run layer
# ---------------------------------------------------------------------------

_dry_run_store = {}

def _caget(pv, timeout=5):
    if _EPICS_AVAILABLE:
        return epics.caget(pv, timeout=timeout)
    base = _dry_run_store.setdefault(pv, random.uniform(50.0, 150.0))
    _dry_run_store[pv] = base + random.uniform(-0.5, 0.5)
    return _dry_run_store[pv]

def _caput(pv, value, wait=False):
    if _EPICS_AVAILABLE:
        return epics.caput(pv, value, wait=wait)
    _dry_run_store[pv] = value

# ---------------------------------------------------------------------------
# Config parser
# ---------------------------------------------------------------------------

def parse_config(config_file):
    """
    Parse config file (lines: PV_NAME  %%% COMMENT, sections separated by
    blank lines).  Returns a list of dicts with keys:
        'monitor', 'voltage', 'position', 'setpoint'
    """
    sections = []
    current = {}
    with open(config_file) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                if current:
                    sections.append(current)
                    current = {}
                continue
            if '%%%' not in line:
                continue
            pv_name, _, comment = line.partition('%%%')
            pv_name = pv_name.strip()
            tag = comment.strip().upper()
            if 'NAME TO MONITOR' in tag:
                current['monitor'] = pv_name
            elif 'VOLTAGE PV' in tag:
                current['voltage'] = pv_name
            elif 'POSITION SETPOINT PV' in tag:   # before POSITION PV
                current['setpoint'] = pv_name
            elif 'POSITION PV' in tag:
                current['position'] = pv_name
    if current:
        sections.append(current)
    return sections

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_PV_KEYS = ['monitor', 'voltage', 'position', 'setpoint']

_GREEN  = '\033[92m'
_RED    = '\033[91m'
_YELLOW = '\033[93m'
_CYAN   = '\033[96m'
_BOLD   = '\033[1m'
_RESET  = '\033[0m'

TWEAK_SETTLE = 1.0   # fixed settle time (s) between tweak steps
TWEAK_STEP   = 0.01  # fixed setpoint step size


def _color(val_str, val, target, tolerance):
    if target is None or val is None:
        return val_str
    code = _GREEN if abs(val - target) / abs(target) <= tolerance else _RED
    return f"{code}{val_str}{_RESET}"

# ---------------------------------------------------------------------------
# Per-cycle tweak helper
# ---------------------------------------------------------------------------

def _confirm_step(set_pv, value):
    """Prompt user to confirm a setpoint write.  Returns False if aborted."""
    try:
        input(f"    Apply: set {set_pv} = {value:.6f}?  "
              f"Press Enter to confirm, Ctrl-C to abort... ")
        return True
    except KeyboardInterrupt:
        print(f"\n{_RED}    Aborted by user.{_RESET}")
        return False


def _tweak_one(piezo_n, sec, target, tolerance, pos_min, pos_max, max_steps,
               confirm=False):
    """
    Tweak one piezo until its monitor PV is within tolerance of target.

    Guard rails — any hit returns False (abort; do not proceed to next piezo):
      - pos_min / pos_max exceeded
      - max_steps reached without reaching target
      - error no longer improving

    Returns True only when target is reached within tolerance.
    """
    label  = f"Piezo{piezo_n}"
    mon_pv = sec['monitor']
    set_pv = sec['setpoint']

    current_val = _caget(mon_pv, timeout=5)
    if current_val is None:
        print(f"{_RED}  [{label}] Cannot read monitor PV. Aborting.{_RESET}")
        return False

    start_pos = _caget(set_pv, timeout=5)
    if start_pos is None:
        print(f"{_RED}  [{label}] Cannot read setpoint PV. Aborting.{_RESET}")
        return False

    print(f"{_BOLD}{_YELLOW}  *** TWEAKING {label} — do not touch ***{_RESET}")

    prev_err = abs(current_val - target)

    # --- Probe: try +step first ---
    probe_pos = round(start_pos + TWEAK_STEP, 9)
    if probe_pos < pos_min or probe_pos > pos_max:
        probe_pos = round(start_pos - TWEAK_STEP, 9)   # try −step instead

    if probe_pos < pos_min or probe_pos > pos_max:
        print(f"{_RED}    GUARD RAIL: cannot step in either direction within "
              f"[{pos_min:.4f}, {pos_max:.4f}]. Aborting.{_RESET}")
        return False

    if confirm and not _confirm_step(set_pv, probe_pos):
        return False
    _caput(set_pv, probe_pos, wait=True)
    time.sleep(TWEAK_SETTLE)
    probe_val = _caget(mon_pv, timeout=5)
    if probe_val is None:
        return False
    probe_err = abs(probe_val - target)

    if probe_err < prev_err:
        direction   = +1 if probe_pos > start_pos else -1
        current_pos = probe_pos
        current_val = probe_val
        prev_err    = probe_err
        step_n      = 1
        arrow = '+' if direction == 1 else '−'
        print(f"{_CYAN}    probe  pos={probe_pos:.4f}  monitor={probe_val:.6g}"
              f"  → continuing {arrow}{_RESET}")
    else:
        # Revert and go opposite direction
        direction = -1 if probe_pos > start_pos else +1
        if confirm and not _confirm_step(set_pv, start_pos):
            return False
        _caput(set_pv, start_pos, wait=True)
        time.sleep(TWEAK_SETTLE)
        current_pos = start_pos
        current_val = _caget(mon_pv, timeout=5) or current_val
        prev_err    = abs(current_val - target)
        step_n      = 0
        arrow = '+' if direction == 1 else '−'
        print(f"{_CYAN}    probe  pos={probe_pos:.4f}  monitor={probe_val:.6g}"
              f"  → undo, try {arrow}{_RESET}")

    # --- Step loop ---
    while step_n < max_steps:
        rel_err = abs(current_val - target) / abs(target)
        if rel_err <= tolerance:
            print(f"{_BOLD}{_GREEN}    {label} reached target "
                  f"(error={rel_err*100:.2f}%).{_RESET}")
            return True   # ← success; caller may proceed to next piezo

        next_pos = round(current_pos + direction * TWEAK_STEP, 9)
        if next_pos < pos_min or next_pos > pos_max:
            print(f"{_RED}    GUARD RAIL: position [{next_pos:.4f}] outside "
                  f"[{pos_min:.4f}, {pos_max:.4f}]. Aborting.{_RESET}")
            return False

        if confirm and not _confirm_step(set_pv, next_pos):
            return False
        _caput(set_pv, next_pos, wait=True)
        time.sleep(TWEAK_SETTLE)
        current_val = _caget(mon_pv, timeout=5)
        if current_val is None:
            return False
        current_err = abs(current_val - target)
        step_n += 1
        delta = next_pos - start_pos
        print(f"{_YELLOW}    step {step_n:2d}  pos={next_pos:.4f} (Δ={delta:+.3f})"
              f"  monitor={current_val:.6g}  err={current_err:.4g}{_RESET}")

        if current_err >= prev_err:
            print(f"{_RED}    GUARD RAIL: error not improving. Aborting.{_RESET}")
            return False

        prev_err    = current_err
        current_pos = next_pos

    # max_steps exhausted without reaching target
    print(f"{_RED}    GUARD RAIL: max steps ({max_steps}) reached without "
          f"reaching target. Aborting.{_RESET}")
    return False

# ---------------------------------------------------------------------------
# Shared display + optional tweak loop
# ---------------------------------------------------------------------------

def run_loop(sections, targets, interval=1.0, tolerance=0.05,
             tweak_mode=False, pos_limits=None, max_steps=5, confirm=False):
    """
    Continuous loop shared by both 'monitor' and 'tweak' subcommands.

    Every cycle:
      1. Print all 8 PVs with green/red coloring on monitor values.
      2. (tweak mode only) For each piezo that is out of tolerance,
         call _tweak_one() to attempt up to max_steps adjustments.
    """
    n_pvs = sum(len(s) for s in sections)
    print(f"\n  Tracking {n_pvs} PVs across {len(sections)} section(s)")
    print(f"  Interval  : {interval}s")
    for i, t in enumerate(targets, 1):
        print(f"  Piezo{i} target : {t:.6g}  (±{tolerance*100:.1f}%  "
              f"{_GREEN}green{_RESET} / {_RED}red{_RESET})")

    if tweak_mode:
        print(f"\n  {_BOLD}{_YELLOW}Tweak mode ON{_RESET}")
        print(f"  Settle time : {TWEAK_SETTLE}s (fixed)")
        print(f"  Step size   : {TWEAK_STEP}")
        print(f"  Max steps   : {max_steps} per cycle")
        print(f"  Confirm     : {'ON (will prompt before each caput)' if confirm else 'OFF'}")
        for i, (lo, hi) in enumerate(pos_limits, 1):
            src = "auto" if (hi - lo) == 0.2 else "user"
            print(f"  {_BOLD}{_YELLOW}Piezo{i} pos range : [{lo:.6f}, {hi:.6f}]"
                  f"  ({src}){_RESET}")

    print()
    try:
        mode_label = "tweaking" if tweak_mode else "monitoring"
        input(f"  Press Enter to start {mode_label}, or Ctrl-C to abort... ")
    except KeyboardInterrupt:
        print("\n  Aborted.")
        return
    print(f"\n  Started. Press Ctrl-C to stop.\n")

    try:
        while True:
            print(f"--- {time.strftime('%H:%M:%S')} ---")
            out_of_range = []

            for i, sec in enumerate(sections, 1):
                target = targets[i - 1]
                print(f"  [Piezo{i}]")
                for key in _PV_KEYS:
                    if key not in sec:
                        continue
                    pv  = sec[key]
                    val = _caget(pv, timeout=5)
                    val_str = f"{val:.6g}" if val is not None else "DISCONNECTED"
                    if key == 'monitor':
                        val_str = _color(val_str, val, target, tolerance)
                        if tweak_mode and val is not None:
                            if abs(val - target) / abs(target) > tolerance:
                                out_of_range.append(i)
                    print(f"    {key:8s} : {pv:<42s} = {val_str}")
                print()

            # --- Tweak phase (skipped in monitor mode) ---
            # Always Piezo1 first, then Piezo2.  If a guard rail is hit,
            # abort immediately and do not proceed to the next piezo.
            if tweak_mode and out_of_range:
                for i in sorted(out_of_range):   # ascending: 1 before 2
                    lo, hi = pos_limits[i - 1]
                    success = _tweak_one(i, sections[i - 1], targets[i - 1],
                                         tolerance, lo, hi, max_steps,
                                         confirm=confirm)
                    if not success:
                        print(f"{_BOLD}{_RED}  Tweak cycle aborted after "
                              f"Piezo{i} guard rail. Resuming monitoring.{_RESET}")
                        break
                print()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n  Stopped.")

# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------

def _parse_pair(s, name):
    try:
        vals = [float(v.strip()) for v in s.split(',')]
    except ValueError:
        print(f"ERROR: {name} must be two comma-separated numbers, "
              f"e.g. {name} 100.0,80.0")
        sys.exit(1)
    if len(vals) != 2:
        print(f"ERROR: {name} requires exactly 2 values (got {len(vals)})")
        sys.exit(1)
    return vals


def _default_config():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, 'bkg_hrm_piezo_tweak.py')


def _load_sections(config):
    if not os.path.exists(config):
        print(f"ERROR: Config file not found: {config}")
        sys.exit(1)
    sections = parse_config(config)
    if not sections:
        print("ERROR: No valid sections found in config file.")
        sys.exit(1)
    return sections


def _parse_targets(s):
    targets = _parse_pair(s, '--target')
    return targets

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _add_shared_args(p):
    p.add_argument('--target', type=str, required=True,
                   help='Comma-separated targets for Piezo1,Piezo2 (e.g. 10300,6500)')
    p.add_argument('--tolerance', type=float, default=5.0,
                   help='%% tolerance: green/red threshold (and tweak trigger)')
    p.add_argument('--interval', type=float, default=1.0,
                   help='Display refresh interval in seconds')
    p.add_argument('--config', default=_default_config(),
                   help='Path to PV config file')
    p.add_argument('--dry-run', action='store_true',
                   help='Simulate PV values without EPICS')


def main():
    parser = argparse.ArgumentParser(
        description="HRM piezo monitor / tweaker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # --- monitor ---
    p_mon = sub.add_parser('monitor',
                           help='Display all 8 PVs continuously. No PVs written.',
                           formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_shared_args(p_mon)

    # --- tweak ---
    p_twk = sub.add_parser('tweak',
                           help='Same as monitor, but auto-adjusts when out of tolerance.',
                           formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_shared_args(p_twk)
    p_twk.add_argument('--pos-range', type=float, default=0.1,
                       help='Allowed drive range = current_pos ± pos-range per piezo')
    p_twk.add_argument('--max-steps', type=int, default=5,
                       help='Max setpoint steps per tweak cycle per piezo')
    p_twk.add_argument('--confirm', action='store_true',
                       help='Prompt for user approval before each caput')

    args = parser.parse_args()

    if not args.dry_run and not _EPICS_AVAILABLE:
        print("ERROR: pyepics not installed. Use --dry-run to test without EPICS.")
        sys.exit(1)

    targets  = _parse_targets(args.target)
    sections = _load_sections(args.config)

    if len(sections) < len(targets):
        print(f"ERROR: Config has {len(sections)} section(s) but --target has "
              f"{len(targets)} values.")
        sys.exit(1)

    if args.command == 'monitor':
        run_loop(sections, targets,
                 interval=args.interval,
                 tolerance=args.tolerance / 100.0)

    elif args.command == 'tweak':
        # Read current position for each piezo and compute allowed range
        pos_limits = []
        for i, sec in enumerate(sections, 1):
            cur = _caget(sec['position'], timeout=5)
            if cur is None:
                print(f"ERROR: Cannot read position PV for Piezo{i}: {sec['position']}")
                sys.exit(1)
            lo = round(cur - args.pos_range, 9)
            hi = round(cur + args.pos_range, 9)
            pos_limits.append((lo, hi))

        run_loop(sections, targets,
                 interval=args.interval,
                 tolerance=args.tolerance / 100.0,
                 tweak_mode=True,
                 pos_limits=pos_limits,
                 max_steps=args.max_steps,
                 confirm=args.confirm)


if __name__ == '__main__':
    main()
