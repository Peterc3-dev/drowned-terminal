"""
DROWNED TERMINAL — CMYK Color Engine

All colors defined in CMYK space, converted to RGB for terminal rendering.
CMYK gamut constraint gives the muted, subtractive, ink-on-brass weight
that matches Drowned God's oxidized-mechanical aesthetic.

Three phosphor modes:
  - AMBER:  Alien cinematic universe Nostromo terminal yellow
  - GREEN:  Classic phosphor P1/P3 green (Boo's signature)
  - CYAN:   Turquoise phosphor glow

Plus the Drowned God chrome palette:
  - Copper, brass, verdigris, occult blue, blood red, tarnished silver

The moodbar module bypasses this engine and renders in native RGB —
it's the one element that bleeds through the brass housing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CMYK:
    c: float  # 0.0 - 1.0
    m: float
    y: float
    k: float

    def to_rgb(self) -> tuple[int, int, int]:
        """Convert CMYK to RGB. Subtractive → additive."""
        r = int(255 * (1 - self.c) * (1 - self.k))
        g = int(255 * (1 - self.m) * (1 - self.k))
        b = int(255 * (1 - self.y) * (1 - self.k))
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    def to_hex(self) -> str:
        r, g, b = self.to_rgb()
        return f"#{r:02x}{g:02x}{b:02x}"

    def to_ansi_fg(self) -> str:
        r, g, b = self.to_rgb()
        return f"\033[38;2;{r};{g};{b}m"

    def to_ansi_bg(self) -> str:
        r, g, b = self.to_rgb()
        return f"\033[48;2;{r};{g};{b}m"

    def dim(self, factor: float = 0.5) -> "CMYK":
        """Darken by increasing K channel."""
        new_k = min(1.0, self.k + (1 - self.k) * (1 - factor))
        return CMYK(self.c, self.m, self.y, new_k)

    def brighten(self, factor: float = 0.3) -> "CMYK":
        """Brighten by reducing K channel."""
        new_k = max(0.0, self.k * (1 - factor))
        return CMYK(self.c, self.m, self.y, new_k)


# ═══════════════════════════════════════════════════════════════
# DROWNED GOD CHROME PALETTE (shared across all phosphor modes)
# ═══════════════════════════════════════════════════════════════

CHROME = {
    # Backgrounds — deep, warm near-blacks
    "bg_deep":       CMYK(0.20, 0.15, 0.10, 0.95),  # near-black warm
    "bg_panel":      CMYK(0.15, 0.12, 0.08, 0.90),  # panel background
    "bg_surface":    CMYK(0.10, 0.10, 0.05, 0.85),  # raised surface
    "bg_hover":      CMYK(0.08, 0.08, 0.04, 0.80),  # hover/focus state

    # Metallics — the brass/copper/verdigris family
    "copper":        CMYK(0.00, 0.42, 0.72, 0.28),  # warm copper #b87333
    "brass":         CMYK(0.00, 0.25, 0.85, 0.45),  # aged brass #8b6914
    "bronze":        CMYK(0.00, 0.35, 0.65, 0.40),  # dark bronze
    "verdigris":     CMYK(0.65, 0.10, 0.45, 0.71),  # oxidized green #2d4a3e
    "silver":        CMYK(0.00, 0.00, 0.00, 0.25),  # tarnished silver
    "iron":          CMYK(0.05, 0.05, 0.02, 0.70),  # dark iron

    # Accents — occult/mechanical
    "occult_blue":   CMYK(0.72, 0.38, 0.00, 0.64),  # deep blue #1a3a5c
    "blood":         CMYK(0.00, 0.90, 0.90, 0.45),  # blood red #8b0000
    "apocalypse":    CMYK(0.00, 0.73, 1.00, 0.00),  # warning orange #ff4500
    "gold":          CMYK(0.00, 0.16, 1.00, 0.00),  # active gold #ffd700
    "parchment":     CMYK(0.00, 0.05, 0.15, 0.12),  # aged paper

    # Text
    "text_primary":  CMYK(0.00, 0.00, 0.00, 0.18),  # near-white
    "text_muted":    CMYK(0.05, 0.05, 0.02, 0.50),  # muted grey
    "text_dim":      CMYK(0.05, 0.05, 0.02, 0.70),  # very dim
}


# ═══════════════════════════════════════════════════════════════
# PHOSPHOR MODES — three terminal glow palettes
# Each provides: glow, bright, mid, dim, scanline
# These override the "active element" colors per theme
# ═══════════════════════════════════════════════════════════════

PHOSPHOR = {
    "amber": {
        # Alien cinematic universe — Nostromo terminal amber
        "glow":       CMYK(0.00, 0.25, 0.85, 0.00),  # bright amber
        "bright":     CMYK(0.00, 0.28, 0.80, 0.10),  # strong amber
        "mid":        CMYK(0.00, 0.30, 0.75, 0.35),  # medium amber
        "dim":        CMYK(0.00, 0.25, 0.65, 0.60),  # dim amber
        "scanline":   CMYK(0.00, 0.20, 0.55, 0.80),  # barely visible
        "label":      "WEYLAND-YUTANI AMBER",
        "pip_accent":  CMYK(0.00, 0.35, 0.90, 0.05),  # pip-boy warm
    },
    "green": {
        # Classic phosphor P1 — Boo's signature
        "glow":       CMYK(0.60, 0.00, 0.85, 0.00),  # bright phosphor
        "bright":     CMYK(0.55, 0.00, 0.80, 0.10),  # strong green
        "mid":        CMYK(0.50, 0.00, 0.70, 0.35),  # medium green
        "dim":        CMYK(0.40, 0.00, 0.55, 0.60),  # dim green
        "scanline":   CMYK(0.30, 0.00, 0.40, 0.80),  # barely visible
        "label":      "PHOSPHOR P1 GREEN",
        "pip_accent":  CMYK(0.50, 0.00, 0.90, 0.05),  # pip-boy green
    },
    "cyan": {
        # Turquoise phosphor glow
        "glow":       CMYK(0.70, 0.00, 0.20, 0.00),  # bright turquoise
        "bright":     CMYK(0.65, 0.00, 0.25, 0.10),  # strong cyan
        "mid":        CMYK(0.55, 0.00, 0.22, 0.35),  # medium cyan
        "dim":        CMYK(0.42, 0.00, 0.18, 0.60),  # dim cyan
        "scanline":   CMYK(0.30, 0.00, 0.12, 0.80),  # barely visible
        "label":      "TURQUOISE PHOSPHOR",
        "pip_accent":  CMYK(0.75, 0.00, 0.15, 0.05),  # pip-boy cyan
    },
}


class ThemeEngine:
    """Manages active phosphor mode and provides color lookups."""

    MODES = ("amber", "green", "cyan")

    def __init__(self, mode: str = "amber"):
        self._mode_index = self.MODES.index(mode) if mode in self.MODES else 0
        self._mode = self.MODES[self._mode_index]

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def phosphor(self) -> dict:
        return PHOSPHOR[self._mode]

    def cycle_mode(self) -> str:
        """Cycle to next phosphor mode. Returns new mode name."""
        self._mode_index = (self._mode_index + 1) % len(self.MODES)
        self._mode = self.MODES[self._mode_index]
        return self._mode

    def color(self, name: str) -> CMYK:
        """Get a color by name. Checks phosphor first, then chrome."""
        if name in PHOSPHOR[self._mode]:
            return PHOSPHOR[self._mode][name]
        if name in CHROME:
            return CHROME[name]
        return CHROME["text_muted"]  # fallback

    def rgb(self, name: str) -> tuple[int, int, int]:
        return self.color(name).to_rgb()

    def hex(self, name: str) -> str:
        return self.color(name).to_hex()

    def ansi_fg(self, name: str) -> str:
        return self.color(name).to_ansi_fg()

    def ansi_bg(self, name: str) -> str:
        return self.color(name).to_ansi_bg()

    # Convenience for Textual CSS generation
    def textual_css(self) -> str:
        """Generate Textual CSS variables from current theme."""
        lines = []
        # Chrome colors
        for name, cmyk in CHROME.items():
            lines.append(f"    --{name.replace('_', '-')}: {cmyk.to_hex()};")
        # Phosphor colors
        for name, cmyk in PHOSPHOR[self._mode].items():
            if isinstance(cmyk, CMYK):
                lines.append(f"    --phosphor-{name}: {cmyk.to_hex()};")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# ALIEN CIPHER ALPHABET — APL/Unicode technical symbols
# Used by Alienware and internet alien language communities.
# Maps A-Z to alien glyphs for decorative text rendering.
# ═══════════════════════════════════════════════════════════════

ALIEN_ALPHA = {
    "A": "⏃", "B": "⏚", "C": "☊", "D": "⎅", "E": "⟒",
    "F": "⎎", "G": "☌", "H": "⊑", "I": "⟟", "J": "⟊",
    "K": "☍", "L": "⌰", "M": "⋔", "N": "⋏", "O": "⍜",
    "P": "⌿", "Q": "⍾", "R": "⍀", "S": "⌇", "T": "⏁",
    "U": "⎍", "V": "⎐", "W": "⍙", "X": "⌖", "Y": "⊬",
    "Z": "⋉",
}

# Reverse lookup: alien glyph → Latin letter
ALIEN_DECODE = {v: k for k, v in ALIEN_ALPHA.items()}

# All alien glyphs as a set for fast membership testing
ALIEN_GLYPHS_SET = set(ALIEN_ALPHA.values())

# Alien glyph list for decorative scatter/border generation
ALIEN_GLYPH_LIST = list(ALIEN_ALPHA.values())


def to_alien(text: str) -> str:
    """Convert Latin text to alien cipher glyphs."""
    result = []
    for ch in text.upper():
        if ch in ALIEN_ALPHA:
            result.append(ALIEN_ALPHA[ch])
        elif ch == " ":
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result)


def from_alien(text: str) -> str:
    """Convert alien cipher glyphs back to Latin text."""
    result = []
    for ch in text:
        if ch in ALIEN_DECODE:
            result.append(ALIEN_DECODE[ch])
        elif ch == " ":
            result.append(" ")
        else:
            result.append(ch)
    return "".join(result)


# ═══════════════════════════════════════════════════════════════
# DECORATIVE GLYPHS — Drowned God × Alien × Ancient Tech
#
# Three layers of symbolic vocabulary:
#   1. Occult/Esoteric   — planetary, alchemical, Kabbalistic
#   2. Alien/Technical   — APL operators, alien cipher extras
#   3. Ancient Tech      — engineering, geometric, structural
# ═══════════════════════════════════════════════════════════════

GLYPHS = {
    # ─── Occult / Esoteric ──────────────────────────────────
    "eye":          "◉",
    "eye_tri":      "△",
    "moon":         "☽",
    "sun":          "☉",
    "jupiter":      "♃",
    "saturn":       "♄",
    "venus":        "♀",
    "mars":         "♂",
    "mercury":      "☿",
    "pentagram":    "⛤",
    "ankh":         "☥",
    "star":         "✦",
    "cross":        "✝",
    "infinity":     "∞",
    "omega":        "Ω",
    "delta":        "Δ",
    "sigma":        "Σ",
    "phi":          "Φ",
    "psi":          "Ψ",
    "caduceus":     "☤",
    "skull":        "☠",
    "lightning":    "⚡",
    "star6":        "✡",
    "fleur":        "⚜",
    "trident":      "⟁",
    "triforce":     "⃤",

    # ─── Alien / APL Technical ──────────────────────────────
    # These are the APL and misc technical symbols that give
    # the interface its extraterrestrial machine intelligence feel
    "al_a":         "⏃",
    "al_e":         "⟒",
    "al_i":         "⟟",
    "al_o":         "⍜",
    "al_t":         "⏁",
    "al_n":         "⋏",
    "al_s":         "⌇",
    "al_r":         "⍀",
    "al_h":         "⊑",
    "al_m":         "⋔",
    "al_d":         "⎅",
    "al_k":         "☍",
    "al_g":         "☌",
    "al_p":         "⌿",
    "al_w":         "⍙",
    "al_v":         "⎐",
    "al_x":         "⌖",
    "al_z":         "⋉",
    # APL operators as decorative elements
    "quad":         "⎕",
    "quad_div":     "⌹",
    "iota":         "⍳",
    "rho":          "⍴",
    "circle_star":  "⍟",
    "circle_bar":   "⊖",
    "up_tack":      "⊥",
    "down_tack":    "⊤",
    "left_shoe":    "⊂",
    "right_shoe":   "⊃",
    "encode":       "⊤",
    "decode":       "⊥",
    "domino":       "⌹",
    "lamp":         "⍝",    # comment glyph — the "lamp of wisdom"
    "del":          "∇",
    "del_tilde":    "⍫",
    "quad_equal":   "⌸",
    "circle_stile": "⌽",
    "jot":          "∘",
    "diamond_apl":  "⋄",
    "zilde":        "⍬",
    "alpha_apl":    "⍺",
    "omega_apl":    "⍵",
    "epsilon_bar":  "⍷",
    "iota_bar":     "⍸",
    "squad":        "⌷",
    "grade_up":     "⍋",
    "grade_down":   "⍒",

    # ─── Ancient Technology / Engineering ────────────────────
    "gear":         "⚙",
    "atom":         "⚛",
    "biohazard":    "☣",
    "radioactive":  "☢",
    "recycle":      "♻",
    "helm":         "⎈",
    "tension":      "⏧",
    "earth":        "⏚",    # also alien B
    "antenna":      "⏢",
    "hexagon":      "⬡",
    "diamond":      "◆",
    "diamond_o":    "◇",
    "circle_dot":   "⊙",
    "bullseye":     "◎",
    "lozenge":      "⬠",
    "shield":       "⛨",
    "crosshair":    "⌖",    # also alien X
    "compass":      "⊹",
    "sector":       "⌔",
    "valve":        "⏣",    # hex with center — mechanical valve

    # ─── Arrows / Navigation ────────────────────────────────
    "arrow_r":      "▶",
    "arrow_l":      "◀",
    "arrow_u":      "▲",
    "arrow_d":      "▼",
    "arrow_ne":     "↗",
    "arrow_se":     "↘",
    "dbl_arrow_r":  "⇒",
    "dbl_arrow_l":  "⇐",
    "spiral_cw":    "↻",
    "spiral_ccw":   "↺",

    # ─── Bar / Block Characters ─────────────────────────────
    "bar_full":     "█",
    "bar_3_4":      "▓",
    "bar_half":     "▒",
    "bar_1_4":      "░",
    "bar_top":      "▀",
    "bar_bot":      "▄",
    "bar_left":     "▌",
    "bar_right":    "▐",

    # ─── Box Drawing (Mechanical Framing) ───────────────────
    "line_h":       "─",
    "line_v":       "│",
    "corner_tl":    "╔",
    "corner_tr":    "╗",
    "corner_bl":    "╚",
    "corner_br":    "╝",
    "line_dh":      "═",
    "line_dv":      "║",
    "tee_l":        "╠",
    "tee_r":        "╣",
    "tee_t":        "╦",
    "tee_b":        "╩",
    "cross_d":      "╬",
    # Single-line variants
    "s_corner_tl":  "┌",
    "s_corner_tr":  "┐",
    "s_corner_bl":  "└",
    "s_corner_br":  "┘",
    "s_tee_l":      "├",
    "s_tee_r":      "┤",
    "s_tee_t":      "┬",
    "s_tee_b":      "┴",
    "s_cross":      "┼",
    # Rounded
    "r_corner_tl":  "╭",
    "r_corner_tr":  "╮",
    "r_corner_bl":  "╰",
    "r_corner_br":  "╯",
}


# ═══════════════════════════════════════════════════════════════
# DECORATIVE BORDER GENERATORS — alien-tech framing
# ═══════════════════════════════════════════════════════════════

import random as _random

# Curated sets for different decorative purposes
ALIEN_BORDER_GLYPHS = [
    "⏃", "⟒", "⟟", "⍜", "⏁", "⋏", "⌇", "⍀", "⊑", "⋔",
    "⎅", "☍", "☌", "⌿", "⍙", "⎐", "⌖", "⋉", "⏚", "⎎",
    "⍾", "⊬", "⟊", "⌰", "⎍",
]

OCCULT_BORDER_GLYPHS = [
    "☽", "☉", "♃", "♄", "♀", "♂", "☿", "⛤", "☥", "✦",
    "∞", "Ω", "Δ", "Σ", "Φ", "Ψ", "◉", "△",
]

TECH_BORDER_GLYPHS = [
    "⎕", "⌹", "⍳", "⍴", "⍟", "⊖", "⊥", "⊤", "⊂", "⊃",
    "∇", "⍫", "⌸", "⌽", "∘", "⋄", "⍬", "⍺", "⍵", "⍷",
    "⍸", "⌷", "⍋", "⍒",
]

ALL_DECORATIVE_GLYPHS = ALIEN_BORDER_GLYPHS + OCCULT_BORDER_GLYPHS + TECH_BORDER_GLYPHS


def alien_border(width: int, style: str = "mixed") -> str:
    """Generate a decorative border line using alien/occult/tech glyphs."""
    if style == "alien":
        pool = ALIEN_BORDER_GLYPHS
    elif style == "occult":
        pool = OCCULT_BORDER_GLYPHS
    elif style == "tech":
        pool = TECH_BORDER_GLYPHS
    else:
        pool = ALL_DECORATIVE_GLYPHS
    return "".join(_random.choice(pool) for _ in range(width))


def alien_scatter(width: int, density: float = 0.3) -> str:
    """Generate a line with scattered alien glyphs at given density."""
    pool = ALL_DECORATIVE_GLYPHS
    line = []
    for _ in range(width):
        if _random.random() < density:
            line.append(_random.choice(pool))
        else:
            line.append(" ")
    return "".join(line)


def alien_frame_top(width: int, title: str = "", style: str = "mixed") -> str:
    """Generate a framed header with alien glyph borders."""
    if title:
        alien_title = to_alien(title)
        pad = width - len(alien_title) - 6
        left = pad // 2
        right = pad - left
        inner = f" ◉ {alien_title} ◉ "
        border_l = alien_border(left, style)
        border_r = alien_border(right, style)
        return f"{border_l}{inner}{border_r}"
    return alien_border(width, style)


def alien_frame_bottom(width: int, style: str = "mixed") -> str:
    """Generate a bottom border with alien glyphs."""
    return alien_border(width, style)

# Roman numeral display for section headers
ROMAN = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
    6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
    11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
    16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
    21: "XXI", 22: "XXII",
}


def roman(n: int) -> str:
    """Convert integer to Roman numeral string."""
    if n in ROMAN:
        return ROMAN[n]
    vals = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
            (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
            (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    result = ""
    for val, sym in vals:
        while n >= val:
            result += sym
            n -= val
    return result
