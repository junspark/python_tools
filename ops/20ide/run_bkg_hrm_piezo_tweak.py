#!/usr/bin/env python3
"""
HRM Background Piezo Monitor & Tweaker

Reads PV names from hrm_piezo_pvs.txt.

Both subcommands run the same continuous display loop (all 8 PVs, green/red
coloring against per-piezo targets).  The only difference is that 'tweak'
automatically adjusts setpoints when a piezo monitor is out of tolerance.

Subcommands
-----------
monitor   Display-only loop.  No PVs are ever written.
tweak     Same display loop, but auto-adjusts setpoints when out of tolerance.

Shared arguments (both subcommands)
------------------------------------
  --target      T1,T2   Per-piezo target values (required)
  --ref-current mA      Reference SR current for normalization (optional)
  --interval    s       Display refresh interval               (default 1 s)
  --config      path    PV config file
  --dry-run             Simulate PV values without EPICS

Tweak-only arguments
--------------------
  --tolerance %       Green/red threshold and tweak trigger  (default 5 %)
  --pos-range  R      Allowed drive range = current_pos ± R  (default 0.1)
  --max-steps  N      Max setpoint steps per tweak cycle     (default 5)
  --settle-time s     Seconds to wait between caput and PV read (default 3 s)
  --confirm           Prompt for approval before each caput    (default off)

Monitor color coding uses a fixed 5 % tolerance (not configurable).

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
import select
import signal
import sys
import termios
import threading
import time
import tty

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

def _log(fh, msg):
    """Write msg to log file (no ANSI codes) with a newline."""
    if fh is not None:
        fh.write(msg + '\n')
        fh.flush()

# ---------------------------------------------------------------------------
# Pause / resume (keyboard listener)
# ---------------------------------------------------------------------------

_pause_event   = threading.Event()
_pause_event.set()    # set = running; clear = paused
_update_limits = threading.Event()  # set on resume to trigger pos_limits refresh


def _start_keyboard_listener():
    """
    Start a daemon thread that watches stdin for 'p' (pause) and 'r' (resume).
    Returns a stop-event; caller sets it to shut the thread down cleanly.
    Terminal settings are restored when the thread exits.
    """
    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    stop = threading.Event()

    def _run():
        try:
            tty.setcbreak(fd)
            while not stop.is_set():
                ready, _, _ = select.select([sys.stdin], [], [], 0.2)
                if ready:
                    ch = sys.stdin.read(1).lower()
                    if ch == 'p' and _pause_event.is_set():
                        _pause_event.clear()
                        print(f"\n  {_BOLD}{_YELLOW}[PAUSED]  Press 'r' to resume...{_RESET}",
                              flush=True)
                    elif ch == 'r' and not _pause_event.is_set():
                        _update_limits.set()
                        _pause_event.set()
                        print(f"\n  {_GREEN}[RESUMED]{_RESET}", flush=True)
                    elif ch in ('q', '\x03'):   # q or Ctrl-C
                        os.kill(os.getpid(), signal.SIGINT)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return stop


def _read_normalized(mon_pv, sr_pv=None, ref_current=None):
    """Read monitor PV and normalize by storage ring current if configured.

    normalized = raw_value * (ref_current / ring_current)

    Returns raw value unchanged if sr_pv / ref_current not configured,
    or if the ring current PV is disconnected / zero.
    """
    val = _caget(mon_pv, timeout=5)
    if val is None or sr_pv is None or ref_current is None:
        return val
    ring_current = _caget(sr_pv, timeout=5)
    if ring_current is None or ring_current <= 0:
        return val
    return val * (ref_current / ring_current)

# ---------------------------------------------------------------------------
# Config parser
# ---------------------------------------------------------------------------

def parse_config(config_file):
    """
    Parse config file (lines: PV_NAME  %%% COMMENT, sections separated by
    blank lines).

    Returns (sr_pv, sections) where:
      sr_pv    : storage ring current PV name, or None if absent
      sections : list of dicts with keys 'monitor', 'voltage', 'position', 'setpoint'
    """
    sr_pv = None
    shutter_pv = None
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
            if 'RING CURRENT PV' in tag:
                sr_pv = pv_name
            elif 'SHUTTER' in tag:
                shutter_pv = pv_name
            elif 'NAME TO MONITOR' in tag:
                current['monitor'] = pv_name
            elif 'VOLTAGE PV' in tag:
                current['voltage'] = pv_name
            elif 'POSITION SETPOINT PV' in tag:   # before POSITION PV
                current['setpoint'] = pv_name
            elif 'POSITION PV' in tag:
                current['position'] = pv_name
    if current:
        sections.append(current)
    return sr_pv, shutter_pv, sections

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

TWEAK_SETTLE_DEFAULT = 3.0   # default settle time (s) between caput and PV read
TWEAK_STEP           = 0.01  # fixed setpoint step size


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
               confirm=False, sr_pv=None, ref_current=None, log_fh=None,
               settle_time=TWEAK_SETTLE_DEFAULT):
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

    current_val = _read_normalized(mon_pv, sr_pv, ref_current)
    if current_val is None:
        print(f"{_RED}  [{label}] Cannot read monitor PV. Aborting.{_RESET}")
        return False

    start_pos = _caget(set_pv, timeout=5)
    if start_pos is None:
        print(f"{_RED}  [{label}] Cannot read setpoint PV. Aborting.{_RESET}")
        return False

    ts = time.strftime('%H:%M:%S')
    msg = f"[{ts}] *** TWEAKING {label} ***"
    print(f"{_BOLD}{_YELLOW}  *** TWEAKING {label} — do not touch ***{_RESET}")
    _log(log_fh, msg)

    prev_err = abs(current_val - target)

    # --- Probe: try +step first ---
    probe_pos = round(start_pos + TWEAK_STEP, 9)
    if probe_pos < pos_min or probe_pos > pos_max:
        probe_pos = round(start_pos - TWEAK_STEP, 9)   # try −step instead

    if probe_pos < pos_min or probe_pos > pos_max:
        msg = (f"[{time.strftime('%H:%M:%S')}]   GUARD RAIL: cannot step in either "
               f"direction within [{pos_min:.4f}, {pos_max:.4f}].")
        print(f"{_RED}    GUARD RAIL: cannot step in either direction within "
              f"[{pos_min:.4f}, {pos_max:.4f}]. Aborting.{_RESET}")
        _log(log_fh, msg)
        return False

    if confirm and not _confirm_step(set_pv, probe_pos):
        return False
    _caput(set_pv, probe_pos, wait=True)
    time.sleep(settle_time)
    probe_val = _read_normalized(mon_pv, sr_pv, ref_current)
    if probe_val is None:
        return False
    probe_err = abs(probe_val - target)

    if probe_err < prev_err:
        direction   = +1 if probe_pos > start_pos else -1
        current_pos = probe_pos
        current_val = probe_val
        prev_err    = probe_err
        step_n      = 1
        arrow = '+' if direction == 1 else '-'
        msg = (f"[{time.strftime('%H:%M:%S')}]   probe  pos={probe_pos:.4f}"
               f"  monitor={probe_val:.6g}  -> continuing {arrow}")
        print(f"{_CYAN}    probe  pos={probe_pos:.4f}  monitor={probe_val:.6g}"
              f"  → continuing {arrow}{_RESET}")
        _log(log_fh, msg)
    else:
        # Revert and go opposite direction
        direction = -1 if probe_pos > start_pos else +1
        if confirm and not _confirm_step(set_pv, start_pos):
            return False
        _caput(set_pv, start_pos, wait=True)
        time.sleep(settle_time)
        current_pos = start_pos
        current_val = _read_normalized(mon_pv, sr_pv, ref_current) or current_val
        prev_err    = abs(current_val - target)
        step_n      = 0
        arrow = '+' if direction == 1 else '-'
        msg = (f"[{time.strftime('%H:%M:%S')}]   probe  pos={probe_pos:.4f}"
               f"  monitor={probe_val:.6g}  -> undo, try {arrow}")
        print(f"{_CYAN}    probe  pos={probe_pos:.4f}  monitor={probe_val:.6g}"
              f"  → undo, try {arrow}{_RESET}")
        _log(log_fh, msg)

    # --- Step loop ---
    best_pos = current_pos   # position with lowest error seen so far
    best_err = prev_err

    while step_n < max_steps:
        rel_err = abs(current_val - target) / abs(target)
        if rel_err <= tolerance:
            msg = (f"[{time.strftime('%H:%M:%S')}]   {label} reached target"
                   f"  (error={rel_err*100:.2f}%)")
            print(f"{_BOLD}{_GREEN}    {label} reached target "
                  f"(error={rel_err*100:.2f}%).{_RESET}")
            _log(log_fh, msg)
            return True

        next_pos = round(current_pos + direction * TWEAK_STEP, 9)
        if next_pos < pos_min or next_pos > pos_max:
            msg = (f"[{time.strftime('%H:%M:%S')}]   GUARD RAIL: position"
                   f" [{next_pos:.4f}] outside [{pos_min:.4f}, {pos_max:.4f}].")
            print(f"{_RED}    GUARD RAIL: position [{next_pos:.4f}] outside "
                  f"[{pos_min:.4f}, {pos_max:.4f}]. Aborting.{_RESET}")
            _log(log_fh, msg)
            return False

        if confirm and not _confirm_step(set_pv, next_pos):
            return False
        _caput(set_pv, next_pos, wait=True)
        time.sleep(settle_time)
        current_val = _read_normalized(mon_pv, sr_pv, ref_current)
        if current_val is None:
            return False
        current_err = abs(current_val - target)
        step_n += 1
        delta = next_pos - start_pos
        msg = (f"[{time.strftime('%H:%M:%S')}]   step {step_n:2d}"
               f"  pos={next_pos:.4f} (D={delta:+.3f})"
               f"  monitor={current_val:.6g}  err={current_err:.4g}")
        print(f"{_YELLOW}    step {step_n:2d}  pos={next_pos:.4f} (Δ={delta:+.3f})"
              f"  monitor={current_val:.6g}  err={current_err:.4g}{_RESET}")
        _log(log_fh, msg)

        if current_err >= prev_err:
            # Peak passed — step back to the best position seen
            msg = (f"[{time.strftime('%H:%M:%S')}]   Peak passed"
                   f" — stepping back to best pos={best_pos:.4f} (err={best_err:.4g})")
            print(f"{_CYAN}    Peak passed — stepping back to best pos={best_pos:.4f}"
                  f"  (err={best_err:.4g}){_RESET}")
            _log(log_fh, msg)
            if confirm and not _confirm_step(set_pv, best_pos):
                return False
            _caput(set_pv, best_pos, wait=True)
            time.sleep(settle_time)
            final_val = _read_normalized(mon_pv, sr_pv, ref_current)
            if final_val is None:
                return False
            final_rel_err = abs(final_val - target) / abs(target)
            if final_rel_err <= tolerance:
                msg = (f"[{time.strftime('%H:%M:%S')}]   {label} at best pos,"
                       f" within tolerance (error={final_rel_err*100:.2f}%)")
                print(f"{_BOLD}{_GREEN}    {label} at best pos, within tolerance "
                      f"(error={final_rel_err*100:.2f}%).{_RESET}")
                _log(log_fh, msg)
                return True
            msg = (f"[{time.strftime('%H:%M:%S')}]   Best position still outside"
                   f" tolerance (error={final_rel_err*100:.2f}%).")
            print(f"{_RED}    Best position still outside tolerance "
                  f"(error={final_rel_err*100:.2f}%). Aborting.{_RESET}")
            _log(log_fh, msg)
            return False

        if current_err < best_err:
            best_err = current_err
            best_pos = next_pos

        prev_err    = current_err
        current_pos = next_pos

    # max_steps exhausted without reaching target
    msg = (f"[{time.strftime('%H:%M:%S')}]   GUARD RAIL: max steps ({max_steps})"
           f" reached without reaching target.")
    print(f"{_RED}    GUARD RAIL: max steps ({max_steps}) reached without "
          f"reaching target. Aborting.{_RESET}")
    _log(log_fh, msg)
    return False

# ---------------------------------------------------------------------------
# Shared display + optional tweak loop
# ---------------------------------------------------------------------------

def run_loop(sections, targets, interval=1.0, tolerance=0.05,
             tweak_mode=False, pos_limits=None, max_steps=5, confirm=False,
             sr_pv=None, ref_current=None, shutter_pv=None, log_fh=None,
             pos_range=None, settle_time=TWEAK_SETTLE_DEFAULT):
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
    print(f"  Keys      : {_BOLD}'p'{_RESET} pause  |  {_BOLD}'r'{_RESET} resume  |  {_BOLD}'q'{_RESET} quit")
    if sr_pv and ref_current is not None:
        print(f"  SR current PV  : {sr_pv}")
        print(f"  Ref current    : {ref_current:.4g} mA  (monitor values normalized to this)")
    if targets is not None:
        for i, t in enumerate(targets, 1):
            print(f"  Piezo{i} target : {t:.6g}  (±{tolerance*100:.1f}%  "
                  f"{_GREEN}green{_RESET} / {_RED}red{_RESET})")
    else:
        print(f"  Targets : not set (raw values displayed, no coloring)")

    if tweak_mode:
        print(f"\n  {_BOLD}{_YELLOW}Tweak mode ON{_RESET}")
        print(f"  Settle time : {settle_time}s")
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
    print(f"\n  Started. Press Ctrl-C to stop  |  "
          f"{_BOLD}'p'{_RESET} = pause  |  {_BOLD}'r'{_RESET} = resume\n")

    norm_active = (sr_pv is not None and ref_current is not None)

    _pause_event.set()   # ensure unpaused at start
    listener_stop = _start_keyboard_listener()

    try:
        while True:
            while not _pause_event.is_set():   # blocks here while paused
                print(f"  {_BOLD}{_YELLOW}[PAUSED]  Press 'r' to resume...{_RESET}",
                      flush=True)
                _pause_event.wait(timeout=5.0)  # re-print reminder every 5 s

            # On resume: refresh pos_limits from current position PV readings
            if tweak_mode and pos_range is not None and _update_limits.is_set():
                _update_limits.clear()
                new_limits = []
                for i, sec in enumerate(sections, 1):
                    cur = _caget(sec['position'], timeout=5)
                    if cur is not None:
                        lo = round(cur - pos_range, 9)
                        hi = round(cur + pos_range, 9)
                        new_limits.append((lo, hi))
                        msg = (f"[{time.strftime('%H:%M:%S')}] Resumed: "
                               f"Piezo{i} pos range updated to [{lo:.6f}, {hi:.6f}]")
                        print(f"  {_CYAN}{msg}{_RESET}")
                        _log(log_fh, msg)
                    else:
                        new_limits.append(pos_limits[i - 1])  # keep old if unreadable
                pos_limits[:] = new_limits   # update in place

            # Read ring current once per cycle
            ring_current = _caget(sr_pv, timeout=5) if norm_active else None
            norm_ok  = norm_active and ring_current is not None and ring_current > 0
            sr_low   = (norm_ok and ring_current < ref_current * 0.90)

            # Check front end shutter — skip tweak if beam is blocked
            shutter_val = _caget(shutter_pv, timeout=5) if shutter_pv else None
            shutter_on  = (shutter_val is not None and
                           (shutter_val == 1 or str(shutter_val).upper() == 'ON'))

            # Cycle header
            ts = time.strftime('%H:%M:%S')
            if norm_active:
                sr_str = f"{ring_current:.2f}" if ring_current is not None else "?"
                hdr = f"--- {ts} ---  SR: {sr_str} mA / ref: {ref_current:.4g} mA"
                print(hdr)
                _log(log_fh, f"\n## {hdr}")
            else:
                hdr = f"--- {ts} ---"
                print(hdr)
                _log(log_fh, f"\n## {hdr}")

            out_of_range = []
            eff_targets  = []   # normalized targets for this cycle (one per piezo)

            for i, sec in enumerate(sections, 1):
                target = targets[i - 1] if targets is not None else None
                eff_target = (target * (ring_current / ref_current)
                              if (norm_ok and target is not None) else target)
                eff_targets.append(eff_target)

                print(f"  [Piezo{i}]")
                _log(log_fh, f"\n**[Piezo{i}]**")
                for key in _PV_KEYS:
                    if key not in sec:
                        continue
                    pv  = sec[key]
                    val = _caget(pv, timeout=5)
                    if key == 'monitor':
                        val_str = f"{val:.6g}" if val is not None else "DISCONNECTED"
                        if norm_ok:
                            val_str += (f"  target={target:.6g}"
                                        f"  norm={eff_target:.6g}")
                        val_str_plain = val_str   # save before ANSI wrapping
                        val_str = _color(val_str, val, eff_target, tolerance)
                        if tweak_mode and val is not None:
                            if abs(val - eff_target) / abs(eff_target) > tolerance:
                                out_of_range.append(i)
                    else:
                        val_str = f"{val:.6g}" if val is not None else "DISCONNECTED"
                        val_str_plain = val_str
                    print(f"    {key:8s} : {pv:<42s} = {val_str}")
                    _log(log_fh, f"- `{key}` : `{pv}` = {val_str_plain}")
                print()

            # --- Tweak phase (skipped in monitor mode) ---
            # Always Piezo1 first, then Piezo2.
            skip_tweak = sr_low or shutter_on
            if tweak_mode and skip_tweak:
                reasons = []
                if sr_low:
                    reasons.append(f"SR current ({ring_current:.2f} mA) "
                                   f">10% below ref ({ref_current:.4g} mA)")
                if shutter_on:
                    reasons.append("front end shutter is ON")
                msg = "Tweak skipped: " + " and ".join(reasons) + "."
                print(f"  {_BOLD}{_YELLOW}{msg}{_RESET}")
                _log(log_fh, f"> {msg}")

            if tweak_mode and out_of_range and not skip_tweak:
                for i in sorted(out_of_range):   # ascending: 1 before 2
                    lo, hi = pos_limits[i - 1]
                    success = _tweak_one(i, sections[i - 1], eff_targets[i - 1],
                                         tolerance, lo, hi, max_steps,
                                         confirm=confirm,
                                         sr_pv=sr_pv, ref_current=ref_current,
                                         log_fh=log_fh,
                                         settle_time=settle_time)
                    if not success:
                        msg = f"Piezo{i} tweak ended without reaching target."
                        print(f"{_BOLD}{_RED}  {msg} Continuing.{_RESET}")
                        _log(log_fh, f"> {msg}")
                print()

            print(f"  {_BOLD}{_GREEN}'p' pause  |  'r' resume  |  'q' quit{_RESET}\n")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n  Stopped.")
        _log(log_fh, "\n---\nSession stopped by user.")
    finally:
        listener_stop.set()   # shut down keyboard listener thread

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
    return os.path.join(here, 'hrm_piezo_pvs.txt')


def _load_config(config):
    if not os.path.exists(config):
        print(f"ERROR: Config file not found: {config}")
        sys.exit(1)
    sr_pv, shutter_pv, sections = parse_config(config)
    if not sections:
        print("ERROR: No valid sections found in config file.")
        sys.exit(1)
    return sr_pv, shutter_pv, sections


def _parse_targets(s):
    targets = _parse_pair(s, '--target')
    return targets

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_MONITOR_TOLERANCE = 0.05   # fixed 5 % for green/red coloring in monitor mode

_LOG_BASE = '/home/beams/S20IDUSER/new_data'

def _add_shared_args(p):
    p.add_argument('--ref-current', type=float, default=None, metavar='mA',
                   help='Reference storage ring current in mA for normalization '
                        '(requires RING CURRENT PV in config)')
    p.add_argument('--expid', type=str, default=None, metavar='NAME',
                   help='Experiment ID — log is written to '
                        f'{_LOG_BASE}/<NAME>/hrm_auto_tweak_record.md')
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
    p_mon.add_argument('--target', type=str, default=None,
                       help='Comma-separated targets for Piezo1,Piezo2 (optional — '
                            'omit to display raw values without coloring)')

    # --- tweak ---
    p_twk = sub.add_parser('tweak',
                           help='Same as monitor, but auto-adjusts when out of tolerance.',
                           formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_shared_args(p_twk)
    p_twk.add_argument('--target', type=str, required=True,
                       help='Comma-separated targets for Piezo1,Piezo2 (e.g. 10300,6500)')
    p_twk.add_argument('--tolerance', type=float, default=5.0,
                       help='%% tolerance: tweak trigger and green/red threshold')
    p_twk.add_argument('--pos-range', type=float, default=0.1,
                       help='Allowed drive range = current_pos ± pos-range per piezo')
    p_twk.add_argument('--max-steps', type=int, default=5,
                       help='Max setpoint steps per tweak cycle per piezo')
    p_twk.add_argument('--settle-time', type=float, default=TWEAK_SETTLE_DEFAULT,
                       help='Seconds to wait between caput and PV read')
    p_twk.add_argument('--confirm', action='store_true',
                       help='Prompt for user approval before each caput')

    args = parser.parse_args()

    if not args.dry_run and not _EPICS_AVAILABLE:
        print("ERROR: pyepics not installed. Use --dry-run to test without EPICS.")
        sys.exit(1)

    targets = _parse_targets(args.target) if args.target else None
    sr_pv, shutter_pv, sections = _load_config(args.config)
    ref_current                = args.ref_current

    if sr_pv and ref_current is None:
        print("WARNING: SR current PV found in config but --ref-current not given. "
              "Normalization disabled.")

    if targets is not None and len(sections) < len(targets):
        print(f"ERROR: Config has {len(sections)} section(s) but --target has "
              f"{len(targets)} values.")
        sys.exit(1)

    # --- Open log file if --expid given ---
    log_fh = None
    if args.expid:
        log_dir  = os.path.join(_LOG_BASE, args.expid)
        log_path = os.path.join(log_dir, 'hrm_auto_tweak_record.md')
        os.makedirs(log_dir, exist_ok=True)
        log_fh = open(log_path, 'a')
        start_ts = time.strftime('%Y-%m-%d %H:%M:%S')
        log_fh.write(f"\n# HRM Piezo Tweak Record\n")
        log_fh.write(f"- **Started** : {start_ts}\n")
        log_fh.write(f"- **Exp ID**  : {args.expid}\n")
        log_fh.write(f"- **Mode**    : {args.command}\n")
        log_fh.write(f"- **Targets** : {args.target}\n")
        if ref_current is not None:
            log_fh.write(f"- **Ref SR current** : {ref_current:.4g} mA\n")
        log_fh.write("\n---\n")
        log_fh.flush()
        print(f"  Log file : {log_path}")

    try:
        if args.command == 'monitor':
            run_loop(sections, targets,
                     interval=args.interval,
                     tolerance=_MONITOR_TOLERANCE,
                     sr_pv=sr_pv,
                     ref_current=ref_current,
                     shutter_pv=shutter_pv,
                     log_fh=log_fh)

        elif args.command == 'tweak':
            # Read current position for each piezo and compute allowed range
            pos_limits = []
            for i, sec in enumerate(sections, 1):
                cur = _caget(sec['position'], timeout=5)
                if cur is None:
                    print(f"ERROR: Cannot read position PV for Piezo{i}: "
                          f"{sec['position']}")
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
                     confirm=args.confirm,
                     sr_pv=sr_pv,
                     ref_current=ref_current,
                     shutter_pv=shutter_pv,
                     log_fh=log_fh,
                     pos_range=args.pos_range,
                     settle_time=args.settle_time)
    finally:
        if log_fh:
            log_fh.close()


if __name__ == '__main__':
    main()
