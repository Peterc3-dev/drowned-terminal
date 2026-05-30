"""Unit tests for core.colors — pure CMYK/cipher/numeral logic.

These exercise only standard-library-backed code (dataclasses, random).
No Textual/Rich/aiohttp or any GPU/model dependency is imported.
"""

from core.colors import (
    CMYK,
    ThemeEngine,
    from_alien,
    roman,
    to_alien,
)


# ── CMYK colour maths ────────────────────────────────────────────

def test_cmyk_to_rgb_pure_black():
    # Full key channel collapses every component to 0.
    assert CMYK(0.0, 0.0, 0.0, 1.0).to_rgb() == (0, 0, 0)


def test_cmyk_to_rgb_pure_white():
    # No ink and no key leaves full white.
    assert CMYK(0.0, 0.0, 0.0, 0.0).to_rgb() == (255, 255, 255)


def test_cmyk_to_rgb_primary_channels():
    # Cyan removes red, magenta removes green, yellow removes blue.
    assert CMYK(1.0, 0.0, 0.0, 0.0).to_rgb() == (0, 255, 255)
    assert CMYK(0.0, 1.0, 0.0, 0.0).to_rgb() == (255, 0, 255)
    assert CMYK(0.0, 0.0, 1.0, 0.0).to_rgb() == (255, 255, 0)


def test_cmyk_to_rgb_clamped_to_byte_range():
    r, g, b = CMYK(0.0, 0.0, 0.0, 0.0).to_rgb()
    assert all(0 <= v <= 255 for v in (r, g, b))


def test_cmyk_to_hex_format():
    assert CMYK(0.0, 0.0, 0.0, 0.0).to_hex() == "#ffffff"
    assert CMYK(0.0, 0.0, 0.0, 1.0).to_hex() == "#000000"


def test_cmyk_ansi_escape_sequences():
    fg = CMYK(0.0, 0.0, 0.0, 0.0).to_ansi_fg()
    bg = CMYK(0.0, 0.0, 0.0, 0.0).to_ansi_bg()
    assert fg == "\033[38;2;255;255;255m"
    assert bg == "\033[48;2;255;255;255m"


def test_cmyk_dim_increases_key_and_stays_in_range():
    base = CMYK(0.1, 0.2, 0.3, 0.4)
    dimmed = base.dim(0.5)
    assert dimmed.k > base.k
    assert 0.0 <= dimmed.k <= 1.0
    # Chromatic channels are untouched by dimming.
    assert (dimmed.c, dimmed.m, dimmed.y) == (base.c, base.m, base.y)


def test_cmyk_brighten_reduces_key():
    base = CMYK(0.1, 0.2, 0.3, 0.8)
    brighter = base.brighten(0.5)
    assert brighter.k < base.k
    assert brighter.k >= 0.0


def test_cmyk_is_frozen():
    import dataclasses

    c = CMYK(0.1, 0.1, 0.1, 0.1)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        c.c = 0.9  # type: ignore[misc]


# ── Alien cipher round-trip ──────────────────────────────────────

def test_to_alien_then_from_alien_round_trips():
    assert from_alien(to_alien("HELLO WORLD")) == "HELLO WORLD"


def test_to_alien_preserves_spaces_and_unknown_chars():
    # Digits and punctuation are passed through unchanged.
    assert to_alien("A 1!") == to_alien("A") + " 1!"


def test_to_alien_uppercases_input():
    assert to_alien("abc") == to_alien("ABC")


# ── Roman numerals ───────────────────────────────────────────────

def test_roman_small_table_values():
    assert roman(1) == "I"
    assert roman(4) == "IV"
    assert roman(9) == "IX"
    assert roman(22) == "XXII"


def test_roman_large_values_via_algorithm():
    # Above the lookup table the subtractive algorithm kicks in.
    assert roman(40) == "XL"
    assert roman(90) == "XC"
    assert roman(2024) == "MMXXIV"


# ── ThemeEngine ──────────────────────────────────────────────────

def test_theme_engine_defaults_to_amber():
    assert ThemeEngine().mode == "amber"


def test_theme_engine_unknown_mode_falls_back_to_amber():
    assert ThemeEngine("nonexistent").mode == "amber"


def test_theme_engine_cycles_through_all_modes():
    eng = ThemeEngine("amber")
    seen = [eng.mode]
    for _ in range(len(ThemeEngine.MODES)):
        seen.append(eng.cycle_mode())
    # Cycling wraps back to the start.
    assert seen[0] == seen[-1] == "amber"
    assert set(seen) == set(ThemeEngine.MODES)


def test_theme_engine_color_lookup_falls_back_to_text_muted():
    eng = ThemeEngine("green")
    # Unknown name returns the muted-text chrome colour, never raises.
    assert isinstance(eng.color("does-not-exist"), CMYK)


def test_theme_engine_phosphor_color_lookup():
    eng = ThemeEngine("green")
    # "glow" lives in the phosphor table and resolves to a CMYK colour.
    assert isinstance(eng.color("glow"), CMYK)
