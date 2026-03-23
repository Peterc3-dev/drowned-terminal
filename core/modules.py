"""
DROWNED TERMINAL — Module System

Every panel in the TUI is a Module. Modules are:
  - Self-contained Textual widgets
  - Registered in the ModuleRegistry
  - Loadable/unloadable at runtime
  - Navigable via keyboard (Esc to back out)
  - Theme-aware (receive ThemeEngine reference)

Module categories:
  - STEM (Chemistry, Physics, Engineering, etc.)
  - Professional (Hacking, Prompt Engineering, SoftDev)
  - Tools (Music Player, Retune432, Animation Station)
  - Status (Daily Quests / Pip-Boy, Netscape Health)
  - Builder (Module Builder — meta-module for adding new ones)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from textual.widget import Widget
from textual.widgets import Static

if TYPE_CHECKING:
    from core.colors import ThemeEngine


@dataclass
class ModuleInfo:
    """Metadata about a registered module."""
    id: str                     # unique slug: "stem.chemistry"
    name: str                   # display name: "Chemistry"
    category: str               # parent: "STEM", "Professional", "Tools", etc.
    description: str = ""       # one-liner
    icon: str = "◆"             # glyph from GLYPHS
    roman_num: int = 0          # section number for display
    keybind: str = ""           # shortcut key if any
    widget_class: type = None   # the Textual Widget subclass
    enabled: bool = True
    locked: bool = False        # future: unlock via daily quests?


class ModuleRegistry:
    """Central registry for all TUI modules."""

    def __init__(self):
        self._modules: dict[str, ModuleInfo] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, info: ModuleInfo):
        """Register a module."""
        self._modules[info.id] = info
        if info.category not in self._categories:
            self._categories[info.category] = []
        if info.id not in self._categories[info.category]:
            self._categories[info.category].append(info.id)

    def get(self, module_id: str) -> ModuleInfo | None:
        return self._modules.get(module_id)

    def list_category(self, category: str) -> list[ModuleInfo]:
        ids = self._categories.get(category, [])
        return [self._modules[mid] for mid in ids if mid in self._modules]

    def all_categories(self) -> list[str]:
        return list(self._categories.keys())

    def all_modules(self) -> list[ModuleInfo]:
        return list(self._modules.values())


class BaseModule(Static):
    """
    Base class for all TUI modules.

    Modules render inside a bordered panel in the tiling layout.
    Pressing Enter on a module in the hub expands it to full focus.
    Pressing Esc backs out to the hub.

    Subclass this and implement:
      - compose() — your module's widget tree
      - on_mount() — initialization
      - on_focus() / on_blur() — focus state changes
    """

    # Subclasses should set these
    MODULE_ID: str = "base"
    MODULE_NAME: str = "Base Module"
    MODULE_CATEGORY: str = "System"

    def __init__(self, theme: "ThemeEngine", **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        self._focused = False

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            id=self.MODULE_ID,
            name=self.MODULE_NAME,
            category=self.MODULE_CATEGORY,
            widget_class=type(self),
        )

    def render_header(self) -> str:
        """Render the module's header bar with glyph and name."""
        info = self.module_info
        p = self.theme.phosphor
        glow = self.theme.color("glow")
        copper = self.theme.color("copper")
        return (
            f"{copper.to_ansi_fg()}╔{'═' * 40}╗\033[0m\n"
            f"{copper.to_ansi_fg()}║{glow.to_ansi_fg()} {info.icon} {info.name.upper()}"
            f"{' ' * (37 - len(info.name))}"
            f"{copper.to_ansi_fg()}║\033[0m"
        )


# ═══════════════════════════════════════════════════════════════
# PRE-REGISTERED MODULE STUBS
# ═══════════════════════════════════════════════════════════════

# These define the module tree. Actual implementations are in modules/

STEM_MODULES = [
    ModuleInfo("stem.chemistry", "Chemistry", "STEM",
               "Molecular structures, reactions, periodic table",
               icon="⚛", roman_num=1),
    ModuleInfo("stem.physics", "Physics", "STEM",
               "Mechanics, electromagnetism, thermodynamics",
               icon="Δ", roman_num=2),
    ModuleInfo("stem.engineering", "Engineering", "STEM",
               "Systems design, materials, structures",
               icon="⚙", roman_num=3),
    ModuleInfo("stem.thermodynamics", "Thermodynamics", "STEM",
               "Heat, entropy, energy transfer",
               icon="☉", roman_num=4),
    ModuleInfo("stem.quantum", "Quantum Mechanics", "STEM",
               "Wave functions, uncertainty, entanglement",
               icon="Ψ", roman_num=5),
    ModuleInfo("stem.strings", "String Theory", "STEM",
               "Extra dimensions, branes, M-theory",
               icon="∞", roman_num=6),
]

PROFESSIONAL_MODULES = [
    ModuleInfo("pro.hacking", "Hacking / Bug Bounty", "Professional",
               "OWASP, Burp Suite, HackerOne targets",
               icon="☠", roman_num=1, keybind="h"),
    ModuleInfo("pro.prompt_eng", "Prompt Engineering", "Professional",
               "System prompts, chain-of-thought, tool use",
               icon="Φ", roman_num=2, keybind="p"),
    ModuleInfo("pro.softdev", "Software Development", "Professional",
               "Python, Rust, systems architecture",
               icon="Σ", roman_num=3, keybind="s"),
]

TOOL_MODULES = [
    ModuleInfo("tools.music", "Music Player", "Tools",
               "Pluggable player with moodbar visualizer",
               icon="♫", roman_num=1, keybind="m"),
    ModuleInfo("tools.retune432", "Retune 432Hz", "Tools",
               "Batch 440→432Hz audio converter",
               icon="♭", roman_num=2),
    ModuleInfo("tools.animation", "Animation Station", "Tools",
               "3D visualizations — physics-defying color & geometry",
               icon="✦", roman_num=3, keybind="a"),
    ModuleInfo("tools.video", "Video Player", "Tools",
               "Stremio/mpv/VLC — anime, streams, media",
               icon="▶", roman_num=4, keybind="v"),
]

STATUS_MODULES = [
    ModuleInfo("status.pipboy", "Daily Quests", "Status",
               "Pip-Boy: bank, pay cycle, weather, hunger, thirst",
               icon="◉", roman_num=1, keybind="d"),
    ModuleInfo("status.netscape", "Netscape Health", "Status",
               "Mesh node status, routing, heartbeats",
               icon="⚡", roman_num=2, keybind="n"),
]

META_MODULES = [
    ModuleInfo("meta.builder", "Module Builder", "Meta",
               "Add new modules and modify the TUI",
               icon="⚙", roman_num=1, keybind="b"),
]

ALL_DEFAULT_MODULES = (
    STEM_MODULES + PROFESSIONAL_MODULES +
    TOOL_MODULES + STATUS_MODULES + META_MODULES
)


def create_default_registry() -> ModuleRegistry:
    """Create and populate the default module registry."""
    registry = ModuleRegistry()
    for mod in ALL_DEFAULT_MODULES:
        registry.register(mod)
    return registry
