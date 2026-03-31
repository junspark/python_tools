#!/usr/bin/env python3
"""
Play a short MIDI tune when a scan finishes.

This module is intentionally dependency-light:
- It generates a tiny MIDI file on the fly (no external Python packages needed).
- It tries common Linux MIDI players in order: timidity, aplaymidi, fluidsynth.
- If no player is available, it falls back to terminal bell notifications.

Typical usage inside your scan script:

    from scan_finish_midi import notify_scan_finished

    # ... scan logic ...
    notify_scan_finished()
"""

import argparse
import os
import shutil
import struct
import subprocess
import tempfile
from typing import Iterable, List, Optional, Sequence, Tuple

# (midi_note, beat_length)
DEFAULT_TUNE: List[Tuple[int, float]] = [
    (72, 0.25),  # C5
    (76, 0.25),  # E5
    (79, 0.25),  # G5
    (84, 0.50),  # C6
    (79, 0.25),
    (84, 0.75),
]


def _vlq(value: int) -> bytes:
    """Encode an int as a MIDI variable-length quantity."""
    if value < 0:
        raise ValueError("VLQ cannot encode negative values")
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.reverse()
    return bytes(out)


def _build_midi_bytes(
    notes: Sequence[Tuple[int, float]],
    bpm: int = 132,
    velocity: int = 96,
    ticks_per_quarter: int = 480,
) -> bytes:
    """Build a minimal format-0 MIDI byte stream from note data."""
    if bpm <= 0:
        raise ValueError("bpm must be > 0")

    us_per_quarter = int(60_000_000 / bpm)

    track = bytearray()

    # Tempo meta event at delta=0
    track.extend(_vlq(0))
    track.extend(b"\xFF\x51\x03")
    track.extend(us_per_quarter.to_bytes(3, "big"))

    # Acoustic Grand Piano program at delta=0 (channel 0)
    track.extend(_vlq(0))
    track.extend(b"\xC0\x00")

    for midi_note, beats in notes:
        if beats <= 0:
            continue
        duration_ticks = max(1, int(round(beats * ticks_per_quarter)))

        # Note on, delta 0
        track.extend(_vlq(0))
        track.extend(bytes([0x90, midi_note & 0x7F, velocity & 0x7F]))

        # Note off after duration
        track.extend(_vlq(duration_ticks))
        track.extend(bytes([0x80, midi_note & 0x7F, 0x40]))

    # End-of-track meta event
    track.extend(_vlq(0))
    track.extend(b"\xFF\x2F\x00")

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks_per_quarter)
    track_chunk = b"MTrk" + struct.pack(">I", len(track)) + bytes(track)
    return header + track_chunk


def _choose_player(preferred: Optional[str] = None) -> Optional[List[str]]:
    """Return command prefix for an available MIDI player."""
    player_map = {
        "timidity": ["timidity", "-q"],
        "aplaymidi": ["aplaymidi"],
        "fluidsynth": ["fluidsynth", "-i"],
    }

    if preferred:
        cmd = player_map.get(preferred)
        if cmd and shutil.which(cmd[0]):
            return cmd

    for name in ("timidity", "aplaymidi", "fluidsynth"):
        cmd = player_map[name]
        if shutil.which(cmd[0]):
            return cmd

    return None


def notify_scan_finished(
    tune: Optional[Sequence[Tuple[int, float]]] = None,
    bpm: int = 132,
    preferred_player: Optional[str] = None,
    repeat: int = 1,
    bell_fallback_count: int = 3,
) -> bool:
    """
    Play the scan-finished tune.

    Returns True if a MIDI player succeeded, False if bell fallback was used.
    """
    if repeat < 1:
        repeat = 1

    notes = list(tune or DEFAULT_TUNE)
    midi_data = _build_midi_bytes(notes, bpm=bpm)
    player_cmd = _choose_player(preferred=preferred_player)

    if not player_cmd:
        for _ in range(max(1, bell_fallback_count)):
            print("\a", end="", flush=True)
        print("No MIDI player found (timidity/aplaymidi/fluidsynth). Bell fallback used.")
        return False

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp.write(midi_data)
        midi_path = tmp.name

    try:
        for _ in range(repeat):
            subprocess.run(player_cmd + [midi_path], check=False)
        return True
    finally:
        try:
            os.remove(midi_path)
        except OSError:
            pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play a short MIDI tune for scan-finished notification.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--bpm", type=int, default=132, help="Tune speed")
    parser.add_argument(
        "--player",
        choices=["timidity", "aplaymidi", "fluidsynth"],
        default=None,
        help="Preferred player; auto-detect if omitted",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Number of repeats")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    ok = notify_scan_finished(
        bpm=args.bpm,
        preferred_player=args.player,
        repeat=args.repeat,
    )
    if ok:
        print("Scan-finished MIDI tune played.")


if __name__ == "__main__":
    main()
