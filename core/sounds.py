"""
DROWNED TERMINAL — Sound Engine

Synthesized sound effects inspired by Drowned God's
mechanical-occult atmosphere. No external audio files needed.

Sounds are generated as WAV bytes and played via aplay/paplay.
Each sound is designed to evoke specific Drowned God moments:

  portal_open   — Bequest Globe valve opening, whooshing air + metallic groan
  portal_close  — Reverse whoosh, mechanical clunk
  click         — Cryptowheel disc engaging, brass on brass
  hover         — Faint electrical hum when cursor moves
  alert         — Occult warning tone, low drone + high ping
  ambient       — Background atmosphere, low rumble + distant mechanisms
  unlock        — Tarot card revealed, crystalline chime
  error         — Mechanical failure, grinding buzz

Usage:
  from core.sounds import SoundEngine
  sfx = SoundEngine()
  sfx.play("portal_open")
  sfx.play("click")
"""

import struct
import math
import random
import subprocess
import tempfile
import os
import threading
from pathlib import Path

SAMPLE_RATE = 22050
CACHE_DIR = Path.home() / ".netscape" / "sounds"


def _sin(freq: float, t: float, phase: float = 0.0) -> float:
    return math.sin(2 * math.pi * freq * t + phase)


def _noise() -> float:
    return random.uniform(-1.0, 1.0)


def _envelope(t: float, attack: float, decay: float,
              sustain: float, release: float, total: float) -> float:
    """ADSR envelope."""
    if t < attack:
        return t / attack
    elif t < attack + decay:
        return 1.0 - (1.0 - sustain) * ((t - attack) / decay)
    elif t < total - release:
        return sustain
    else:
        remaining = total - t
        return sustain * (remaining / release) if release > 0 else 0.0


def _to_wav(samples: list[float], sample_rate: int = SAMPLE_RATE) -> bytes:
    """Convert float samples (-1.0 to 1.0) to 16-bit WAV bytes."""
    num_samples = len(samples)
    data_size = num_samples * 2
    file_size = 36 + data_size

    header = struct.pack('<4sI4s', b'RIFF', file_size, b'WAVE')
    fmt = struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, 1,
                      sample_rate, sample_rate * 2, 2, 16)
    data_header = struct.pack('<4sI', b'data', data_size)

    pcm = bytearray()
    for s in samples:
        s = max(-1.0, min(1.0, s))
        pcm.extend(struct.pack('<h', int(s * 32767)))

    return header + fmt + data_header + bytes(pcm)


# ═══════════════════════════════════════════════════════════════
# SOUND GENERATORS
# ═══════════════════════════════════════════════════════════════

def gen_portal_open(duration: float = 1.2) -> list[float]:
    """Bequest Globe valve opening — whoosh + metallic resonance."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = _envelope(t, 0.05, 0.2, 0.6, 0.4, duration)

        # Rising whoosh (filtered noise with rising pitch)
        whoosh = _noise() * 0.3 * env
        # Apply crude low-pass by averaging
        rise = min(1.0, t / duration)

        # Metallic resonance — two detuned sines
        metal = (_sin(180 + rise * 120, t) * 0.15 +
                 _sin(267 + rise * 80, t) * 0.1) * env

        # Sub bass thud at start
        thud = _sin(45, t) * max(0, 1.0 - t * 4) * 0.4

        # High harmonic shimmer
        shimmer = _sin(1200 + rise * 800, t) * 0.05 * env * rise

        samples.append(whoosh + metal + thud + shimmer)
    return samples


def gen_portal_close(duration: float = 0.8) -> list[float]:
    """Reverse whoosh + mechanical clunk."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        fall = 1.0 - (t / duration)
        env = _envelope(t, 0.02, 0.1, 0.5, 0.3, duration)

        whoosh = _noise() * 0.25 * env * fall
        metal = _sin(280 - fall * 100, t) * 0.12 * env

        # Clunk at end
        clunk_t = duration - 0.08
        clunk = 0.0
        if t > clunk_t:
            ct = t - clunk_t
            clunk = _sin(85, ct) * max(0, 1.0 - ct * 20) * 0.5

        samples.append(whoosh + metal + clunk)
    return samples


def gen_click(duration: float = 0.08) -> list[float]:
    """Cryptowheel brass click."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = max(0, 1.0 - t * 25)

        click = (_sin(2400, t) * 0.3 + _sin(4800, t) * 0.15 +
                 _noise() * 0.15) * env
        body = _sin(800, t) * 0.2 * env

        samples.append(click + body)
    return samples


def gen_hover(duration: float = 0.04) -> list[float]:
    """Faint electrical hum on cursor move."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = max(0, 1.0 - t / duration)
        hum = _sin(3200, t) * 0.06 * env
        samples.append(hum)
    return samples


def gen_alert(duration: float = 0.6) -> list[float]:
    """Occult warning — low drone + high ping."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = _envelope(t, 0.01, 0.05, 0.7, 0.3, duration)

        drone = (_sin(65, t) + _sin(97.5, t) * 0.5) * 0.2 * env
        ping = _sin(1800, t) * max(0, 1.0 - t * 5) * 0.3
        overtone = _sin(2700, t) * max(0, 1.0 - t * 8) * 0.1

        samples.append(drone + ping + overtone)
    return samples


def gen_unlock(duration: float = 0.5) -> list[float]:
    """Tarot card revealed — crystalline chime."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = max(0, 1.0 - t / duration) ** 1.5

        chime = (_sin(1047, t) * 0.2 +  # C6
                 _sin(1319, t) * 0.15 +  # E6
                 _sin(1568, t) * 0.12 +  # G6
                 _sin(2093, t) * 0.08)   # C7
        chime *= env

        sparkle = _sin(4186, t) * max(0, 1.0 - t * 10) * 0.1

        samples.append(chime + sparkle)
    return samples


def gen_error(duration: float = 0.3) -> list[float]:
    """Mechanical failure — grinding buzz."""
    n = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = _envelope(t, 0.01, 0.05, 0.8, 0.1, duration)

        buzz = (_sin(110, t) * 0.2 + _sin(165, t) * 0.15 +
                _noise() * 0.15) * env

        # Harsh overtones
        grind = _sin(440, t) * _sin(7, t) * 0.1 * env

        samples.append(buzz + grind)
    return samples


# ═══════════════════════════════════════════════════════════════
# SOUND ENGINE
# ═══════════════════════════════════════════════════════════════

SOUND_GENERATORS = {
    "portal_open": gen_portal_open,
    "portal_close": gen_portal_close,
    "click": gen_click,
    "hover": gen_hover,
    "alert": gen_alert,
    "unlock": gen_unlock,
    "error": gen_error,
}


class SoundEngine:
    """Plays synthesized sound effects. Caches WAV files on disk."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cache: dict[str, Path] = {}
        self._player = self._detect_player()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Pre-generate and cache all sounds
        for name, gen_fn in SOUND_GENERATORS.items():
            wav_path = CACHE_DIR / f"{name}.wav"
            if not wav_path.exists():
                samples = gen_fn()
                wav_bytes = _to_wav(samples)
                wav_path.write_bytes(wav_bytes)
            self._cache[name] = wav_path

    def _detect_player(self) -> str:
        """Find available audio player command."""
        for cmd in ["paplay", "aplay", "pw-play"]:
            try:
                result = subprocess.run(
                    ["which", cmd], capture_output=True, timeout=2
                )
                if result.returncode == 0:
                    return cmd
            except Exception:
                pass
        return ""

    def play(self, name: str):
        """Play a sound effect (non-blocking)."""
        if not self.enabled or not self._player:
            return
        path = self._cache.get(name)
        if not path or not path.exists():
            return

        def _play():
            try:
                subprocess.run(
                    [self._player, str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            except Exception:
                pass

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()

    def toggle(self):
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        return self.enabled


if __name__ == "__main__":
    import sys
    import time

    sfx = SoundEngine()
    print(f"Audio player: {sfx._player or 'NONE'}")
    print(f"Cached sounds: {list(sfx._cache.keys())}")

    if len(sys.argv) > 1:
        name = sys.argv[1]
        if name == "all":
            for snd in SOUND_GENERATORS:
                print(f"  Playing: {snd}")
                sfx.play(snd)
                time.sleep(1.5)
        elif name in SOUND_GENERATORS:
            print(f"  Playing: {name}")
            sfx.play(name)
            time.sleep(2)
        else:
            print(f"  Unknown: {name}")
            print(f"  Available: {list(SOUND_GENERATORS.keys())}")
    else:
        print("Usage: python3 sounds.py [name|all]")
        print(f"  Available: {list(SOUND_GENERATORS.keys())}")
