"""
DROWNED TERMINAL — Room Map

3D navigable map showing all modules as rooms in a spatial layout.
The user's current position is highlighted. Rooms connected by corridors.
Rendered as ASCII wireframe with spectral color depth cues.

The map is a Bionic Commando-style node graph rendered with
pseudo-3D perspective. Each room is a node. Connections show
which rooms lead to which. The current room pulses.

Layout:
  The rooms are arranged in a 3D space projected to 2D.
  Categories cluster together. Z-depth adds parallax.

  Professional ──── STEM
       │               │
     Tools ─── Status ── Meta
"""

import math
import time
from dataclasses import dataclass

from core.colors import ThemeEngine, CHROME, to_alien


def ansi_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


RESET = "\033[0m"


@dataclass
class RoomNode:
    id: str
    name: str
    icon: str
    category: str
    x: float  # 3D position
    y: float
    z: float  # depth (0 = front, 1 = back)
    connections: list[str]  # IDs of connected rooms


# ═══════════════════════════════════════════════════════════════
# ROOM LAYOUT — spatial positions for all modules
# ═══════════════════════════════════════════════════════════════

ROOMS = [
    # Professional cluster — front left
    RoomNode("pro.hacking", "Hacking", "☠", "Professional",
             -0.6, -0.3, 0.2, ["pro.prompt_eng", "pro.softdev", "tools.music"]),
    RoomNode("pro.prompt_eng", "Prompts", "Φ", "Professional",
             -0.4, -0.5, 0.1, ["pro.hacking", "pro.softdev", "stem.quantum"]),
    RoomNode("pro.softdev", "SoftDev", "Σ", "Professional",
             -0.3, -0.1, 0.3, ["pro.hacking", "pro.prompt_eng", "tools.video"]),

    # STEM cluster — back right
    RoomNode("stem.chemistry", "Chem", "⚛", "STEM",
             0.5, -0.4, 0.5, ["stem.physics", "stem.engineering"]),
    RoomNode("stem.physics", "Physics", "Δ", "STEM",
             0.7, -0.2, 0.6, ["stem.chemistry", "stem.quantum", "stem.thermodynamics"]),
    RoomNode("stem.engineering", "Engin", "⚙", "STEM",
             0.6, 0.0, 0.4, ["stem.chemistry", "stem.thermodynamics"]),
    RoomNode("stem.thermodynamics", "Thermo", "☉", "STEM",
             0.8, 0.1, 0.7, ["stem.physics", "stem.engineering", "stem.strings"]),
    RoomNode("stem.quantum", "Quantum", "Ψ", "STEM",
             0.4, -0.6, 0.3, ["stem.physics", "pro.prompt_eng"]),
    RoomNode("stem.strings", "Strings", "∞", "STEM",
             0.9, 0.3, 0.8, ["stem.thermodynamics"]),

    # Tools cluster — front center
    RoomNode("tools.music", "Music", "♫", "Tools",
             -0.1, 0.2, 0.1, ["tools.video", "tools.animation", "pro.hacking"]),
    RoomNode("tools.video", "Video", "▶", "Tools",
             0.1, 0.3, 0.15, ["tools.music", "pro.softdev", "tools.animation"]),
    RoomNode("tools.animation", "Anim", "✦", "Tools",
             0.0, 0.5, 0.2, ["tools.music", "tools.video"]),
    RoomNode("tools.retune432", "432Hz", "♭", "Tools",
             -0.2, 0.4, 0.25, ["tools.music"]),

    # Status — center
    RoomNode("status.pipboy", "Quests", "◉", "Status",
             0.0, -0.1, 0.0, ["status.netscape", "pro.hacking", "tools.music"]),
    RoomNode("status.netscape", "Netscape", "⚡", "Status",
             0.2, -0.15, 0.05, ["status.pipboy", "stem.chemistry"]),

    # Meta — back center
    RoomNode("meta.builder", "Builder", "⚙", "Meta",
             0.0, 0.0, 0.9, ["status.pipboy"]),
]

ROOM_LOOKUP = {r.id: r for r in ROOMS}


def render_room_map(w: int, h: int, current_room: str,
                    theme: ThemeEngine, t: float = 0.0) -> list[str]:
    """
    Render the 3D room map as ASCII art.
    Current room pulses. Depth affects brightness.
    """
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2

    glow_rgb = theme.color("glow").to_rgb()
    copper_rgb = CHROME["copper"].to_rgb()
    brass_rgb = CHROME["brass"].to_rgb()

    # Project 3D positions to 2D with perspective
    projected = {}
    for room in ROOMS:
        # Simple perspective: farther rooms are smaller and more centered
        depth_scale = 1.0 - room.z * 0.4
        sx = int(cx + room.x * (w * 0.4) * depth_scale)
        sy = int(cy + room.y * (h * 0.4) * depth_scale)
        projected[room.id] = (sx, sy, room.z)

    # Draw connections first (behind rooms)
    for room in ROOMS:
        sx1, sy1, z1 = projected[room.id]
        for conn_id in room.connections:
            if conn_id in projected:
                sx2, sy2, z2 = projected[conn_id]
                # Only draw each connection once
                if room.id < conn_id:
                    avg_z = (z1 + z2) / 2
                    brightness = max(0.15, 0.5 - avg_z * 0.4)
                    cr = int(copper_rgb[0] * brightness)
                    cg = int(copper_rgb[1] * brightness)
                    cb = int(copper_rgb[2] * brightness)
                    steps = max(abs(sx2 - sx1), abs(sy2 - sy1), 1)
                    for s in range(steps + 1):
                        f = s / max(steps, 1)
                        px = int(sx1 + (sx2 - sx1) * f)
                        py = int(sy1 + (sy2 - sy1) * f)
                        if 0 <= px < w and 0 <= py < h:
                            if canvas[py][px] == " ":
                                canvas[py][px] = f"{ansi_fg(cr, cg, cb)}·{RESET}"

    # Draw rooms
    for room in ROOMS:
        sx, sy, z = projected[room.id]
        is_current = (room.id == current_room)

        # Depth-based brightness
        brightness = max(0.3, 1.0 - z * 0.6)

        if is_current:
            # Pulsing glow for current room
            pulse = 0.7 + 0.3 * math.sin(t * 3)
            r = int(glow_rgb[0] * pulse)
            g = int(glow_rgb[1] * pulse)
            b = int(glow_rgb[2] * pulse)
        else:
            r = int(brass_rgb[0] * brightness)
            g = int(brass_rgb[1] * brightness)
            b = int(brass_rgb[2] * brightness)

        # Draw room icon
        if 0 <= sx < w and 0 <= sy < h:
            canvas[sy][sx] = f"{ansi_fg(r, g, b)}{room.icon}{RESET}"

        # Draw room name (to the right of icon)
        name = room.name[:8]
        for ci, ch in enumerate(name):
            nx = sx + ci + 2
            if 0 <= nx < w and 0 <= sy < h:
                nr = int(r * 0.7) if not is_current else r
                ng = int(g * 0.7) if not is_current else g
                nb = int(b * 0.7) if not is_current else b
                canvas[sy][nx] = f"{ansi_fg(nr, ng, nb)}{ch}{RESET}"

        # Draw bracket around current room
        if is_current:
            if sx - 1 >= 0 and sy < h:
                canvas[sy][sx - 1] = f"{ansi_fg(r, g, b)}[{RESET}"
            end_x = sx + len(name) + 2
            if end_x < w and sy < h:
                canvas[sy][end_x] = f"{ansi_fg(r, g, b)}]{RESET}"

    return ["".join(row) for row in canvas]


def render_room_map_plain(w: int, h: int, current_room: str) -> list[str]:
    """Render without ANSI colors — for plain text contexts."""
    canvas = [[" "] * w for _ in range(h)]
    cx, cy = w // 2, h // 2

    projected = {}
    for room in ROOMS:
        ds = 1.0 - room.z * 0.4
        sx = int(cx + room.x * (w * 0.4) * ds)
        sy = int(cy + room.y * (h * 0.4) * ds)
        projected[room.id] = (sx, sy)

    for room in ROOMS:
        sx1, sy1 = projected[room.id]
        for conn_id in room.connections:
            if conn_id in projected and room.id < conn_id:
                sx2, sy2 = projected[conn_id]
                steps = max(abs(sx2 - sx1), abs(sy2 - sy1), 1)
                for s in range(steps + 1):
                    f = s / max(steps, 1)
                    px = int(sx1 + (sx2 - sx1) * f)
                    py = int(sy1 + (sy2 - sy1) * f)
                    if 0 <= px < w and 0 <= py < h and canvas[py][px] == " ":
                        canvas[py][px] = "·"

    for room in ROOMS:
        sx, sy = projected[room.id]
        is_current = (room.id == current_room)
        if 0 <= sx < w and 0 <= sy < h:
            canvas[sy][sx] = room.icon
        marker = f"[{room.name}]" if is_current else room.name
        for ci, ch in enumerate(marker):
            nx = sx + ci + 1
            if 0 <= nx < w and 0 <= sy < h:
                canvas[sy][nx] = ch

    return ["".join(row) for row in canvas]


if __name__ == "__main__":
    import sys
    import os

    current = sys.argv[1] if len(sys.argv) > 1 else "status.pipboy"
    w, h = os.get_terminal_size()
    h -= 1
    theme = ThemeEngine("amber")

    print("\033[?25l", end="")
    t = 0.0
    try:
        while True:
            lines = render_room_map(w, h, current, theme, t)
            frame = "\n".join(lines)
            print(f"\033[H{frame}", end="", flush=True)
            time.sleep(0.05)
            t += 0.05
    except KeyboardInterrupt:
        print("\033[?25h\033[2J\033[H", end="")
