"""
DROWNED TERMINAL — Video Player Module

Pluggable video player container with Stremio integration.
Stremio exposes a local HTTP API on port 11470 when running.

This module:
  - Detects if Stremio server is running
  - Queries current playback state
  - Browses installed addons and catalogs
  - Launches Stremio with a selected stream
  - Also supports mpv, vlc, or any CLI player

The actual video renders in its own window (can't do video in terminal).
This module is the REMOTE CONTROL — shows what's playing, queue, controls.
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass


STREMIO_API = "http://localhost:11470"


@dataclass
class PlaybackState:
    title: str = ""
    series: str = ""
    episode: str = ""
    state: str = "stopped"     # playing, paused, stopped
    position_sec: float = 0.0
    duration_sec: float = 0.0
    player: str = "none"       # stremio, mpv, vlc


def check_stremio() -> bool:
    """Check if Stremio server is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "2", f"{STREMIO_API}/stats.json"],
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except Exception:
        return False


def stremio_search(query: str) -> list[dict]:
    """Search Stremio catalogs."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "5",
             f"{STREMIO_API}/api/addonCollectionGet"],
            capture_output=True, text=True, timeout=6
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data
    except Exception:
        pass
    return []


def launch_in_mpv(url: str, title: str = ""):
    """Launch a stream URL in mpv."""
    cmd = ["mpv", "--title", title or "Drowned Terminal", url]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def launch_in_vlc(url: str, title: str = ""):
    """Launch a stream URL in VLC."""
    cmd = ["vlc", "--meta-title", title or "Drowned Terminal", url]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# Player adapter registry
PLAYER_COMMANDS = {
    "mpv": lambda url, title: launch_in_mpv(url, title),
    "vlc": lambda url, title: launch_in_vlc(url, title),
    "stremio": lambda url, title: subprocess.Popen(
        ["xdg-open", f"stremio://detail/{url}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ),
}


def render_video_panel(width: int = 58) -> str:
    """Render the video module panel."""
    stremio_up = check_stremio()
    status = "◉ ONLINE" if stremio_up else "○ OFFLINE"

    lines = [
        f"  ╔{'═' * (width - 4)}╗",
        f"  ║{'▶  V I D E O  ▶':^{width - 4}}║",
        f"  ╠{'═' * (width - 4)}╣",
        f"  ║{' ' * (width - 4)}║",
        f"  ║  {'Stremio Server:':<18} {status:<{width - 24}}║",
        f"  ║{' ' * (width - 4)}║",
        f"  ║  {'Now Playing:':<18} {'Nothing':<{width - 24}}║",
        f"  ║  {'Player:':<18} {'Not connected':<{width - 24}}║",
        f"  ║{' ' * (width - 4)}║",
        f"  ╠{'═' * (width - 4)}╣",
        f"  ║  {'[1] Launch Stremio':<{width - 6}}║",
        f"  ║  {'[2] Play URL in mpv':<{width - 6}}║",
        f"  ║  {'[3] Play URL in VLC':<{width - 6}}║",
        f"  ║  {'[s] Search anime':<{width - 6}}║",
        f"  ║  {'[q] Queue management':<{width - 6}}║",
        f"  ╚{'═' * (width - 4)}╝",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_video_panel())
    print(f"\n  Stremio running: {check_stremio()}")
