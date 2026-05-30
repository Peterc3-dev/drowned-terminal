"""Unit tests for core.sounds pure DSP helpers.

Only the standard-library-backed signal generation is tested here
(struct/math/random). The SoundEngine class is intentionally NOT
instantiated: it touches the filesystem and external audio players,
which are environment-dependent and out of scope for unit tests.
"""

import struct

from core.sounds import (
    SAMPLE_RATE,
    SOUND_GENERATORS,
    _envelope,
    _to_wav,
)


# ── ADSR envelope ────────────────────────────────────────────────

def test_envelope_attack_ramps_from_zero():
    # At t=0 the attack phase starts at silence.
    assert _envelope(0.0, 0.1, 0.1, 0.6, 0.2, 1.0) == 0.0


def test_envelope_peaks_at_one_at_end_of_attack():
    assert _envelope(0.1, 0.1, 0.1, 0.6, 0.2, 1.0) == 1.0


def test_envelope_holds_sustain_level():
    # Comfortably inside the sustain region.
    assert _envelope(0.5, 0.1, 0.1, 0.6, 0.2, 1.0) == 0.6


def test_envelope_decays_toward_release_end():
    # Just before total duration the release has driven it near zero.
    val = _envelope(0.99, 0.1, 0.1, 0.6, 0.2, 1.0)
    assert 0.0 <= val < 0.6


def test_envelope_stays_within_unit_range():
    total = 1.0
    steps = 100
    for i in range(steps + 1):
        t = total * i / steps
        val = _envelope(t, 0.1, 0.1, 0.6, 0.2, total)
        assert -0.001 <= val <= 1.001


# ── WAV serialisation ────────────────────────────────────────────

def test_to_wav_has_riff_wave_header():
    wav = _to_wav([0.0, 0.0, 0.0])
    assert wav[0:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_to_wav_byte_length_matches_sample_count():
    samples = [0.0] * 10
    wav = _to_wav(samples)
    # 44-byte canonical header + 16-bit (2 byte) PCM per sample.
    assert len(wav) == 44 + len(samples) * 2


def test_to_wav_declares_expected_format_fields():
    wav = _to_wav([0.0])
    # fmt chunk: audio_format=1 (PCM), channels=1, bits=16.
    audio_format, channels = struct.unpack("<HH", wav[20:24])
    bits_per_sample = struct.unpack("<H", wav[34:36])[0]
    assert audio_format == 1
    assert channels == 1
    assert bits_per_sample == 16


def test_to_wav_clips_out_of_range_samples():
    # Values beyond [-1, 1] must clamp to the 16-bit extremes, not overflow.
    wav = _to_wav([5.0, -5.0])
    s1, s2 = struct.unpack("<hh", wav[44:48])
    assert s1 == 32767
    assert s2 == -32767


# ── generators ───────────────────────────────────────────────────

def test_all_generators_produce_nonempty_bounded_samples():
    for name, gen in SOUND_GENERATORS.items():
        samples = gen()
        assert samples, f"{name} produced no samples"
        # Generators may sum partials above 1.0; the WAV writer clips,
        # but raw output should still be finite and reasonably bounded.
        assert all(abs(s) < 10.0 for s in samples), name


def test_generator_length_tracks_sample_rate_and_duration():
    from core.sounds import gen_click

    # gen_click defaults to 0.08s; length is round(rate * duration).
    samples = gen_click()
    assert len(samples) == int(SAMPLE_RATE * 0.08)
