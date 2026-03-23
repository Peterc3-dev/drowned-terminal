"""
DROWNED TERMINAL — Daily Quests Module (Pip-Boy)

Styled after the Fallout Pip-Boy interface.
Displays real-time personal stats:

  ◉ Bank Account        — current balance (manual update or API)
  ◉ Next Pay Cycle      — countdown to payday
  ◉ Weather             — local area icon + temp
  ◉ Hunger Meter        — estimated from timing + conversation mentions
  ◉ Thirst Meter        — estimated from timing + conversation mentions
  ◉ Kimi Heartbeat      — last response time from Boo2
  ◉ Netscape Status     — mesh node health summary

All meters use CMYK phosphor colors with brass framing.
"""

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Config file for personal data
PIPBOY_CONFIG = Path.home() / ".netscape" / "pipboy.json"

DEFAULT_PIPBOY = {
    "bank_balance": 0.00,
    "pay_cycle_days": 14,        # biweekly
    "last_payday": "",           # ISO date string
    "next_payday": "",
    "location": "Delray Beach, FL",
    "last_meal_time": "",        # ISO datetime
    "last_drink_time": "",       # ISO datetime
    "meal_interval_hours": 6,    # expected time between meals
    "drink_interval_hours": 3,   # expected time between drinks
}


@dataclass
class PipBoyStats:
    """Current stat snapshot for rendering."""
    bank_balance: float = 0.00
    days_to_payday: int = 0
    next_payday_str: str = ""
    weather_icon: str = "?"
    weather_temp: str = "--°F"
    weather_desc: str = "Unknown"
    hunger_pct: float = 0.0       # 0.0 = just ate, 1.0 = starving
    thirst_pct: float = 0.0       # 0.0 = just drank, 1.0 = dehydrated
    kimi_last_heartbeat: str = "Unknown"
    kimi_status: str = "Offline"
    netscape_nodes_online: int = 0
    netscape_nodes_total: int = 0


def load_pipboy_config() -> dict:
    if PIPBOY_CONFIG.exists():
        with open(PIPBOY_CONFIG) as f:
            return {**DEFAULT_PIPBOY, **json.load(f)}
    PIPBOY_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPBOY_CONFIG, "w") as f:
        json.dump(DEFAULT_PIPBOY, f, indent=2)
    return DEFAULT_PIPBOY.copy()


def save_pipboy_config(config: dict):
    PIPBOY_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPBOY_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


def calculate_hunger(last_meal: str, interval_hours: float) -> float:
    """Calculate hunger as 0.0-1.0 based on time since last meal."""
    if not last_meal:
        return 0.5  # unknown, show middle
    try:
        then = datetime.fromisoformat(last_meal)
        elapsed = (datetime.now() - then).total_seconds() / 3600
        return min(1.0, max(0.0, elapsed / interval_hours))
    except Exception:
        return 0.5


def calculate_thirst(last_drink: str, interval_hours: float) -> float:
    """Calculate thirst as 0.0-1.0 based on time since last drink."""
    if not last_drink:
        return 0.5
    try:
        then = datetime.fromisoformat(last_drink)
        elapsed = (datetime.now() - then).total_seconds() / 3600
        return min(1.0, max(0.0, elapsed / interval_hours))
    except Exception:
        return 0.5


def days_until_payday(next_payday: str) -> int:
    """Days until next payday."""
    if not next_payday:
        return -1
    try:
        target = datetime.fromisoformat(next_payday).date()
        today = datetime.now().date()
        delta = (target - today).days
        return max(0, delta)
    except Exception:
        return -1


def render_meter(value: float, width: int = 20, filled: str = "█",
                 empty: str = "░") -> str:
    """Render a horizontal meter bar."""
    filled_count = int(value * width)
    empty_count = width - filled_count
    return filled * filled_count + empty * empty_count


def render_pipboy_ascii(stats: PipBoyStats, width: int = 60) -> str:
    """
    Render the full Pip-Boy panel as ASCII art.
    This gets wrapped in CMYK phosphor colors by the module widget.
    """
    w = width
    sep = f"  ╠{'═' * (w - 4)}╣"
    blank = f"  ║{' ' * (w - 4)}║"

    # Hunger/thirst labels
    hunger_label = "SATED" if stats.hunger_pct < 0.3 else (
        "HUNGRY" if stats.hunger_pct < 0.7 else "STARVING"
    )
    thirst_label = "HYDRATED" if stats.thirst_pct < 0.3 else (
        "THIRSTY" if stats.thirst_pct < 0.7 else "DEHYDRATED"
    )

    lines = [
        f"  ╔{'═' * (w - 4)}╗",
        f"  ║{'◉  D A I L Y   Q U E S T S  ◉':^{w - 4}}║",
        f"  ║{'[ P I P - B O Y  3 0 0 0 ]':^{w - 4}}║",
        sep,
        blank,
        f"  ║  {'CAPS:':<14} ${stats.bank_balance:>10,.2f}{' ' * (w - 32)}║",
        f"  ║  {'PAY CYCLE:':<14} {stats.days_to_payday:>3}d  ({stats.next_payday_str}){' ' * max(0, w - 42 - len(stats.next_payday_str))}║",
        blank,
        sep,
        blank,
        f"  ║  {'WEATHER:':<14} {stats.weather_icon} {stats.weather_temp}  {stats.weather_desc:<{w - 38}}║",
        blank,
        sep,
        blank,
        f"  ║  {'HUNGER:':<14} [{render_meter(stats.hunger_pct, 20)}] {hunger_label:<{w - 44}}║",
        f"  ║  {'THIRST:':<14} [{render_meter(stats.thirst_pct, 20)}] {thirst_label:<{w - 44}}║",
        blank,
        sep,
        blank,
        f"  ║  {'KIMI STATUS:':<14} {stats.kimi_status:<{w - 20}}║",
        f"  ║  {'LAST SIGNAL:':<14} {stats.kimi_last_heartbeat:<{w - 20}}║",
        blank,
        sep,
        blank,
        f"  ║  {'NETSCAPE:':<14} {stats.netscape_nodes_online}/{stats.netscape_nodes_total} nodes online{' ' * max(0, w - 38)}║",
        blank,
        f"  ╚{'═' * (w - 4)}╝",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI COMMANDS — for updating stats from terminal
# ═══════════════════════════════════════════════════════════════

def cmd_ate():
    """Record a meal."""
    config = load_pipboy_config()
    config["last_meal_time"] = datetime.now().isoformat()
    save_pipboy_config(config)
    print("◉ Meal logged.")


def cmd_drank():
    """Record a drink."""
    config = load_pipboy_config()
    config["last_drink_time"] = datetime.now().isoformat()
    save_pipboy_config(config)
    print("◉ Drink logged.")


def cmd_bank(amount: float):
    """Update bank balance."""
    config = load_pipboy_config()
    config["bank_balance"] = amount
    save_pipboy_config(config)
    print(f"◉ Balance: ${amount:,.2f}")


def cmd_payday(date_str: str):
    """Set next payday (YYYY-MM-DD)."""
    config = load_pipboy_config()
    config["next_payday"] = date_str
    save_pipboy_config(config)
    print(f"◉ Next payday: {date_str}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # Demo render
        stats = PipBoyStats(
            bank_balance=1247.83,
            days_to_payday=6,
            next_payday_str="2026-03-11",
            weather_icon="⛅",
            weather_temp="78°F",
            weather_desc="Partly Cloudy",
            hunger_pct=0.45,
            thirst_pct=0.3,
            kimi_status="Online",
            kimi_last_heartbeat="2m ago",
            netscape_nodes_online=1,
            netscape_nodes_total=2,
        )
        print(render_pipboy_ascii(stats))
    else:
        cmd = sys.argv[1]
        if cmd == "ate":
            cmd_ate()
        elif cmd == "drank":
            cmd_drank()
        elif cmd == "bank" and len(sys.argv) > 2:
            cmd_bank(float(sys.argv[2]))
        elif cmd == "payday" and len(sys.argv) > 2:
            cmd_payday(sys.argv[2])
        else:
            print("Usage: pipboy.py [ate|drank|bank <amount>|payday <YYYY-MM-DD>]")
