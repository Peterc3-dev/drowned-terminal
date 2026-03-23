"""
DROWNED TERMINAL — Animation Engine

Physics-defying 3D visualizations.
Each animation renders to a list of strings (one per row).
Can be embedded in grid cells at small sizes or run fullscreen.

Animations:
  tesseract  — Rotating 4D hypercube
  helix      — DNA double helix, spectral color
  mandala    — Sacred geometry breathing
  wormhole   — Portal tunnel, spiral depth
  sigil      — Rotating occult sigil with orbiting glyphs
"""

import math
import random
import time


def spectral_color(t: float) -> tuple[int, int, int]:
    r = int(128 + 127 * math.sin(2 * math.pi * t))
    g = int(128 + 127 * math.sin(2 * math.pi * t + 2.094))
    b = int(128 + 127 * math.sin(2 * math.pi * t + 4.189))
    return (r, g, b)


def ansi_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


RESET = "\033[0m"


def render_tesseract(w: int, h: int, t: float) -> list[str]:
    """4D hypercube projected to 2D. Returns list of strings."""
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2

    verts_4d = [(x, y, z, ww) for ww in (-1, 1) for z in (-1, 1)
                for y in (-1, 1) for x in (-1, 1)]

    ca, sa = math.cos(t), math.sin(t)
    cb, sb = math.cos(t * 0.7), math.sin(t * 0.7)

    projected = []
    for (x, y, z, ww) in verts_4d:
        x2 = x * ca - ww * sa
        w2 = x * sa + ww * ca
        y2 = y * cb - z * sb
        z2 = y * sb + z * cb
        d4 = max(0.1, 3.0 - w2)
        s4 = 2.0 / d4
        x3, y3, z3 = x2 * s4, y2 * s4, z2 * s4
        d3 = max(0.1, 4.0 - z3)
        s3 = 2.0 / d3
        sx = int(cx + x3 * s3 * (w // 5))
        sy = int(cy + y3 * s3 * (h // 4))
        projected.append((sx, sy, z3))

    # Draw edges
    for i in range(16):
        for j in range(i + 1, 16):
            diff = sum(abs(a - b) for a, b in zip(verts_4d[i], verts_4d[j]))
            if diff == 2:
                x1, y1, z1 = projected[i]
                x2, y2, z2 = projected[j]
                steps = max(abs(x2 - x1), abs(y2 - y1), 1)
                phase = (t * 0.3 + (z1 + z2) / 4) % 1.0
                r, g, b = spectral_color(phase)
                for s in range(steps + 1):
                    f = s / max(steps, 1)
                    px = int(x1 + (x2 - x1) * f)
                    py = int(y1 + (y2 - y1) * f)
                    if 0 <= px < w and 0 <= py < h:
                        bri = max(0.3, 0.5 + (z1 + (z2 - z1) * f) * 0.2)
                        canvas[py][px] = f"{ansi_fg(int(r*bri), int(g*bri), int(b*bri))}·{RESET}"

    for sx, sy, z in projected:
        if 0 <= sx < w and 0 <= sy < h:
            phase = (t * 0.5 + z * 0.3) % 1.0
            r, g, b = spectral_color(phase)
            canvas[sy][sx] = f"{ansi_fg(r, g, b)}◉{RESET}"

    return ["".join(row) for row in canvas]


def render_helix(w: int, h: int, t: float) -> list[str]:
    """Double helix with spectral colors."""
    canvas = [[" "] * w for _ in range(h)]
    cx = w // 2

    for y in range(h):
        phase = (y / max(h, 1)) * math.pi * 4 + t * 2
        x1 = int(cx + math.sin(phase) * (w // 5))
        x2 = int(cx + math.sin(phase + math.pi) * (w // 5))
        cp = ((y / max(h, 1)) + t * 0.1) % 1.0
        r1, g1, b1 = spectral_color(cp)
        r2, g2, b2 = spectral_color((cp + 0.5) % 1.0)

        if 0 <= x1 < w:
            canvas[y][x1] = f"{ansi_fg(r1, g1, b1)}●{RESET}"
        if 0 <= x2 < w:
            canvas[y][x2] = f"{ansi_fg(r2, g2, b2)}●{RESET}"

        if y % 3 == 0:
            s, e = min(x1, x2), max(x1, x2)
            for x in range(s + 1, e):
                if 0 <= x < w:
                    f = (x - s) / max(e - s, 1)
                    mr = int(r1 + (r2 - r1) * f)
                    mg = int(g1 + (g2 - g1) * f)
                    mb = int(b1 + (b2 - b1) * f)
                    canvas[y][x] = f"{ansi_fg(mr, mg, mb)}─{RESET}"

    return ["".join(row) for row in canvas]


def render_mandala(w: int, h: int, t: float) -> list[str]:
    """Sacred geometry breathing."""
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2
    breath = 0.6 + 0.4 * math.sin(t * 0.5)

    for layer in range(5):
        sides = 3 + layer
        radius = (2 + layer * 2) * breath
        offset = t * (0.3 + layer * 0.1) * (1 if layer % 2 == 0 else -1)
        cp = (layer / 5 + t * 0.05) % 1.0
        r, g, b = spectral_color(cp)
        dim = max(0.4, 1.0 - layer * 0.12)
        r, g, b = int(r * dim), int(g * dim), int(b * dim)

        for i in range(sides):
            a1 = (2 * math.pi * i / sides) + offset
            a2 = (2 * math.pi * (i + 1) / sides) + offset
            x1 = cx + radius * math.cos(a1) * 2
            y1 = cy + radius * math.sin(a1)
            x2 = cx + radius * math.cos(a2) * 2
            y2 = cy + radius * math.sin(a2)
            steps = int(max(abs(x2 - x1), abs(y2 - y1), 1))
            for s in range(steps + 1):
                f = s / max(steps, 1)
                px = int(x1 + (x2 - x1) * f)
                py = int(y1 + (y2 - y1) * f)
                if 0 <= px < w and 0 <= py < h:
                    canvas[py][px] = f"{ansi_fg(r, g, b)}◆{RESET}"

    er, eg, eb = spectral_color(t * 0.3 % 1.0)
    if 0 <= cx < w and 0 <= cy < h:
        canvas[cy][cx] = f"{ansi_fg(er, eg, eb)}◉{RESET}"

    return ["".join(row) for row in canvas]


def render_wormhole(w: int, h: int, t: float) -> list[str]:
    """Portal tunnel — spiral depth effect for room transitions."""
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2

    for ring in range(12):
        depth = (ring + t * 3) % 12
        radius = 1 + depth * max(w, h) / 24
        brightness = max(0.1, 1.0 - depth / 12)
        sides = 16

        cp = (depth / 12 + t * 0.2) % 1.0
        r, g, b = spectral_color(cp)
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)

        for i in range(sides):
            angle = (2 * math.pi * i / sides) + t * 0.5 + depth * 0.3
            px = int(cx + radius * math.cos(angle) * 2)
            py = int(cy + radius * math.sin(angle))
            if 0 <= px < w and 0 <= py < h:
                char = "◉" if depth < 2 else "●" if depth < 5 else "·"
                canvas[py][px] = f"{ansi_fg(r, g, b)}{char}{RESET}"

    return ["".join(row) for row in canvas]


def render_sigil(w: int, h: int, t: float) -> list[str]:
    """Rotating occult sigil with orbiting glyphs."""
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2
    glyphs = "☽☉♃♄♀♂☿⛤☥✦Ω∞ΔΣΦΨ◉"

    # Central eye
    er, eg, eb = spectral_color(t * 0.15 % 1.0)
    if 0 <= cx < w and 0 <= cy < h:
        canvas[cy][cx] = f"{ansi_fg(er, eg, eb)}◉{RESET}"

    # Orbiting glyphs
    for i, glyph in enumerate(glyphs):
        orbit = 3 + (i % 3) * 3
        speed = 0.3 + (i % 4) * 0.15
        direction = 1 if i % 2 == 0 else -1
        angle = t * speed * direction + (2 * math.pi * i / len(glyphs))

        px = int(cx + orbit * math.cos(angle) * 2)
        py = int(cy + orbit * math.sin(angle))

        if 0 <= px < w and 0 <= py < h:
            cp = (i / len(glyphs) + t * 0.05) % 1.0
            r, g, b = spectral_color(cp)
            canvas[py][px] = f"{ansi_fg(r, g, b)}{glyph}{RESET}"

    # Connecting lines between adjacent orbiting glyphs
    for i in range(0, len(glyphs) - 1, 3):
        orbit = 3 + (i % 3) * 3
        speed = 0.3 + (i % 4) * 0.15
        a1 = t * speed + (2 * math.pi * i / len(glyphs))
        a2 = t * speed + (2 * math.pi * (i + 1) / len(glyphs))
        x1 = cx + orbit * math.cos(a1) * 2
        y1 = cy + orbit * math.sin(a1)
        x2 = cx + orbit * math.cos(a2) * 2
        y2 = cy + orbit * math.sin(a2)
        steps = int(max(abs(x2 - x1), abs(y2 - y1), 1))
        cp = (i / len(glyphs) + t * 0.03) % 1.0
        r, g, b = spectral_color(cp)
        r, g, b = r // 3, g // 3, b // 3
        for s in range(steps + 1):
            f = s / max(steps, 1)
            px = int(x1 + (x2 - x1) * f)
            py = int(y1 + (y2 - y1) * f)
            if 0 <= px < w and 0 <= py < h and canvas[py][px] == " ":
                canvas[py][px] = f"{ansi_fg(r, g, b)}·{RESET}"

    return ["".join(row) for row in canvas]


# ═══════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════

ANIMATIONS = {
    "tesseract": {"name": "Impossible Geometry", "icon": "◇", "render": render_tesseract},
    "helix": {"name": "Spectral Helix", "icon": "◎", "render": render_helix},
    "mandala": {"name": "Void Mandala", "icon": "◉", "render": render_mandala},
    "wormhole": {"name": "Wormhole Portal", "icon": "⊙", "render": render_wormhole},
    "sigil": {"name": "Occult Sigil", "icon": "⛤", "render": render_sigil},
}


def render_frame_for_cell(anim_key: str, w: int, h: int, t: float) -> list[str]:
    """Render an animation frame sized for a grid cell."""
    anim = ANIMATIONS.get(anim_key, ANIMATIONS["tesseract"])
    return anim["render"](w, h, t)


# ═══════════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import os

    anim_key = sys.argv[1] if len(sys.argv) > 1 else "tesseract"
    if anim_key not in ANIMATIONS:
        print(f"Available: {list(ANIMATIONS.keys())}")
        sys.exit(1)

    anim = ANIMATIONS[anim_key]
    w, h = os.get_terminal_size()
    h -= 1

    print("\033[?25l", end="")  # hide cursor
    t = 0.0
    try:
        while True:
            lines = anim["render"](w, h, t)
            frame = "\n".join(lines)
            print(f"\033[H{frame}", end="", flush=True)
            time.sleep(0.05)
            t += 0.05
    except KeyboardInterrupt:
        print("\033[?25h\033[2J\033[H", end="")
