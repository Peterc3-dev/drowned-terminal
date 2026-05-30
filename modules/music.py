"""
DROWNED TERMINAL — Music Module

Pluggable music player integration with:
  - Moodbar visualizer (native RGB — the one element that bleeds through)
  - Player adapter system (Strawberry, MPD, Spotify, custom)
  - Retune432 integration for on-the-fly 440→432Hz conversion

The moodbar renders in FULL RGB spectral colors.
Everything else (borders, text, controls) uses the CMYK phosphor palette.
This is the crack in the brass housing where raw energy shows through.
"""

import random
from pathlib import Path
from dataclasses import dataclass

RESET = "\033[0m"


@dataclass
class MoodbarData:
    """1000 RGB triplets — the raw moodbar."""
    colors: list[tuple[int, int, int]]  # exactly 1000 entries

    @classmethod
    def from_mood_file(cls, path: Path) -> "MoodbarData":
        """Load a .mood file (3000 bytes: R,G,B × 1000)."""
        data = path.read_bytes()
        if len(data) != 3000:
            raise ValueError(f"Expected 3000 bytes, got {len(data)}")
        colors = []
        for i in range(0, 3000, 3):
            colors.append((data[i], data[i + 1], data[i + 2]))
        return cls(colors=colors)

    @classmethod
    def generate_demo(cls) -> "MoodbarData":
        """Generate a demo moodbar for testing — simulates spectral analysis."""
        colors = []
        # Simulate a song: intro → verse → chorus → verse → chorus → outro
        sections = [
            (100, "intro"),     # quiet, blue-green
            (200, "verse"),     # mid-heavy, green-yellow
            (150, "chorus"),    # full spectrum, bright
            (200, "verse"),     # mid-heavy again
            (150, "chorus"),    # full spectrum
            (100, "bridge"),    # sparse, blue
            (100, "outro"),     # fade to dark
        ]

        for count, section in sections:
            for i in range(count):
                t = i / count  # position within section

                if section == "intro":
                    r = int(20 + 30 * t)
                    g = int(40 + 60 * t)
                    b = int(80 + 40 * t)
                elif section == "verse":
                    r = int(60 + 40 * random.random())
                    g = int(120 + 60 * random.random())
                    b = int(30 + 40 * random.random())
                elif section == "chorus":
                    r = int(180 + 75 * random.random())
                    g = int(120 + 80 * random.random())
                    b = int(60 + 80 * random.random())
                elif section == "bridge":
                    r = int(30 + 20 * random.random())
                    g = int(50 + 40 * random.random())
                    b = int(120 + 80 * random.random())
                elif section == "outro":
                    fade = 1.0 - t
                    r = int(50 * fade + 10 * random.random())
                    g = int(80 * fade + 10 * random.random())
                    b = int(60 * fade + 10 * random.random())
                else:
                    r = g = b = 40

                colors.append((
                    max(0, min(255, r)),
                    max(0, min(255, g)),
                    max(0, min(255, b))
                ))

        return cls(colors=colors)


def render_moodbar_ansi(data: MoodbarData, width: int = 80,
                        height: int = 2, position: float = 0.0) -> str:
    """
    Render moodbar as ANSI true-color text.
    This is NATIVE RGB — it bleeds through the CMYK palette.

    Args:
        data: MoodbarData with 1000 RGB entries
        width: terminal columns to render
        height: rows (2-3 gives that beveled depth)
        position: 0.0-1.0 playback position (dims played portion)
    """
    # Downsample 1000 entries to terminal width
    step = len(data.colors) / width
    sampled = []
    for i in range(width):
        idx = int(i * step)
        # Average a few nearby samples for smoothing
        start = max(0, idx - 1)
        end = min(len(data.colors), idx + 2)
        chunk = data.colors[start:end]
        avg_r = sum(c[0] for c in chunk) // len(chunk)
        avg_g = sum(c[1] for c in chunk) // len(chunk)
        avg_b = sum(c[2] for c in chunk) // len(chunk)
        sampled.append((avg_r, avg_g, avg_b))

    lines = []
    pos_col = int(position * width)

    for row in range(height):
        line = ""
        # Vertical gradient: top row brighter, bottom dimmer
        brightness = 1.0 - (row / height) * 0.35

        for col, (r, g, b) in enumerate(sampled):
            # Apply brightness gradient
            r = int(r * brightness)
            g = int(g * brightness)
            b = int(b * brightness)

            # Dim played portion slightly
            if col < pos_col:
                r = int(r * 0.6)
                g = int(g * 0.6)
                b = int(b * 0.6)

            # Playhead indicator
            if col == pos_col:
                line += "\033[48;2;255;255;255m \033[0m"
            else:
                line += f"\033[48;2;{r};{g};{b}m \033[0m"

        lines.append(line)

    return "\n".join(lines)


def render_music_panel(width: int = 60, theme_mode: str = "amber") -> str:
    """
    Render the complete music module panel.
    Border and text use CMYK phosphor. Moodbar uses native RGB.
    """
    lines = []
    lines.append(f"  ╔{'═' * (width - 4)}╗")
    lines.append(f"  ║{'♫  M U S I C  ♫':^{width - 4}}║")
    lines.append(f"  ╠{'═' * (width - 4)}╣")
    lines.append(f"  ║{' ' * (width - 4)}║")
    lines.append(f"  ║  {'Now Playing:':<{width - 6}}║")
    lines.append(f"  ║  {'  Tool - Lateralus (432Hz)':<{width - 6}}║")
    lines.append(f"  ║{' ' * (width - 4)}║")

    # Moodbar insert (native RGB — bleeds through)
    lines.append(f"  ║  MOODBAR:{' ' * (width - 14)}║")
    # The actual moodbar renders separately in full RGB
    # In the TUI widget, this gets composited
    lines.append(f"  ║  [MOODBAR_RENDER_HERE]{' ' * max(0, width - 27)}║")
    lines.append(f"  ║{' ' * (width - 4)}║")

    # Transport controls
    lines.append(f"  ║  {'◀◀  ▶  ▶▶  ■  🔀  🔁':<{width - 6}}║")
    lines.append(f"  ║  {'03:42 / 09:24':<{width - 6}}║")
    lines.append(f"  ║{' ' * (width - 4)}║")

    # Tools
    lines.append(f"  ╠{'═' * (width - 4)}╣")
    lines.append(f"  ║  {'[r] Retune 432Hz   [p] Player Config':<{width - 6}}║")
    lines.append(f"  ║  {'[v] Visualizer     [l] Library':<{width - 6}}║")
    lines.append(f"  ╚{'═' * (width - 4)}╝")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# PLAYER ADAPTERS — pluggable music player backends
# ═══════════════════════════════════════════════════════════════

class PlayerAdapter:
    """Base class for music player integration."""

    def get_now_playing(self) -> dict:
        """Returns: {title, artist, album, duration_sec, position_sec, state}"""
        return {"title": "Unknown", "artist": "Unknown", "state": "stopped"}

    def play(self): pass
    def pause(self): pass
    def next_track(self): pass
    def prev_track(self): pass
    def seek(self, position_sec: float): pass


class StrawberryAdapter(PlayerAdapter):
    """Adapter for Strawberry Music Player via MPRIS D-Bus."""

    def get_now_playing(self) -> dict:
        try:
            import subprocess
            result = subprocess.run(
                ["dbus-send", "--print-reply", "--dest=org.mpris.MediaPlayer2.strawberry",
                 "/org/mpris/MediaPlayer2", "org.freedesktop.DBus.Properties.Get",
                 "string:org.mpris.MediaPlayer2.Player", "string:Metadata"],
                capture_output=True, text=True, timeout=2
            )
            # Parse D-Bus output (simplified)
            output = result.stdout
            title = artist = "Unknown"
            if "xesam:title" in output:
                title = output.split("xesam:title")[1].split('"')[1]
            if "xesam:artist" in output:
                artist = output.split("xesam:artist")[1].split('"')[1]
            return {"title": title, "artist": artist, "state": "playing"}
        except Exception:
            return {"title": "Strawberry", "artist": "Not connected", "state": "stopped"}


class MPDAdapter(PlayerAdapter):
    """Adapter for MPD via mpc command."""

    def get_now_playing(self) -> dict:
        try:
            import subprocess
            result = subprocess.run(
                ["mpc", "current", "-f", "%title%\t%artist%\t%album%"],
                capture_output=True, text=True, timeout=2
            )
            parts = result.stdout.strip().split("\t")
            return {
                "title": parts[0] if len(parts) > 0 else "Unknown",
                "artist": parts[1] if len(parts) > 1 else "Unknown",
                "album": parts[2] if len(parts) > 2 else "Unknown",
                "state": "playing" if result.stdout.strip() else "stopped",
            }
        except Exception:
            return {"title": "MPD", "artist": "Not connected", "state": "stopped"}


# Registry of available adapters
PLAYER_ADAPTERS = {
    "strawberry": StrawberryAdapter,
    "mpd": MPDAdapter,
    # Future: "spotify", "cmus", "vlc", etc.
}


if __name__ == "__main__":
    # Demo: render moodbar to terminal
    print("\n  ═══ MOODBAR DEMO (Native RGB) ═══\n")
    demo = MoodbarData.generate_demo()
    print(render_moodbar_ansi(demo, width=70, height=3, position=0.4))
    print()
    print(render_music_panel(width=60))
