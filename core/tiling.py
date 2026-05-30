"""
DROWNED TERMINAL — Tiling Engine

Dynamic tiling layout inspired by i3/Hyprland window managers.
Modules are panes that auto-arrange when added or removed.

Layout rules:
  1 pane  → fullscreen
  2 panes → vertical split 50/50
  3 panes → left 50%, right stacked 50% (master-stack)
  4 panes → 2×2 grid
  5+ panes → master left, rest stacked right

Keyboard:
  Ctrl+Enter  → Open module selector
  Ctrl+W      → Close focused pane
  Ctrl+Arrow  → Move focus between panes
  Ctrl+Shift+Arrow → Swap pane positions
  Ctrl+F      → Toggle focused pane fullscreen (zoom)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class SplitDirection(Enum):
    HORIZONTAL = auto()  # left | right
    VERTICAL = auto()    # top / bottom


@dataclass
class TileNode:
    """A node in the tiling tree. Either a leaf (module) or a split."""
    module_id: Optional[str] = None  # leaf node: which module
    split: Optional[SplitDirection] = None  # branch node: split direction
    ratio: float = 0.5  # split ratio (0.0–1.0, position of divider)
    children: list = field(default_factory=list)  # [left/top, right/bottom]
    focused: bool = False
    zoomed: bool = False  # temporarily fullscreen

    @property
    def is_leaf(self) -> bool:
        return self.module_id is not None

    @property
    def is_branch(self) -> bool:
        return self.split is not None and len(self.children) == 2


@dataclass
class Rect:
    """Screen rectangle for a tile."""
    x: int
    y: int
    w: int
    h: int


class TilingLayout:
    """
    Manages the tiling tree and computes layout rectangles.
    
    Usage:
        layout = TilingLayout()
        layout.add("status.pipboy")
        layout.add("tools.music")
        layout.add("pro.hacking")
        rects = layout.compute(screen_width=120, screen_height=40)
        # Returns: {"status.pipboy": Rect(...), "tools.music": Rect(...), ...}
    """

    def __init__(self):
        self.root: Optional[TileNode] = None
        self._focus_id: Optional[str] = None
        self._pane_order: list[str] = []  # insertion order for focus cycling

    @property
    def pane_count(self) -> int:
        return len(self._pane_order)

    @property
    def focused_id(self) -> Optional[str]:
        return self._focus_id

    def add(self, module_id: str):
        """Add a module pane. Auto-arranges based on count."""
        if module_id in self._pane_order:
            self._focus_id = module_id
            return

        self._pane_order.append(module_id)
        self._focus_id = module_id
        self._rebuild_tree()

    def remove(self, module_id: str):
        """Remove a module pane. Auto-rearranges remaining."""
        if module_id not in self._pane_order:
            return
        self._pane_order.remove(module_id)
        if self._focus_id == module_id:
            self._focus_id = self._pane_order[-1] if self._pane_order else None
        self._rebuild_tree()

    def focus_next(self):
        """Cycle focus to next pane."""
        if not self._pane_order:
            return
        if self._focus_id is None:
            self._focus_id = self._pane_order[0]
            return
        idx = self._pane_order.index(self._focus_id)
        self._focus_id = self._pane_order[(idx + 1) % len(self._pane_order)]

    def focus_prev(self):
        """Cycle focus to previous pane."""
        if not self._pane_order:
            return
        if self._focus_id is None:
            self._focus_id = self._pane_order[-1]
            return
        idx = self._pane_order.index(self._focus_id)
        self._focus_id = self._pane_order[(idx - 1) % len(self._pane_order)]

    def swap_with_next(self):
        """Swap focused pane position with next."""
        if not self._focus_id or len(self._pane_order) < 2:
            return
        idx = self._pane_order.index(self._focus_id)
        next_idx = (idx + 1) % len(self._pane_order)
        self._pane_order[idx], self._pane_order[next_idx] = (
            self._pane_order[next_idx], self._pane_order[idx]
        )
        self._rebuild_tree()

    def toggle_zoom(self):
        """Toggle focused pane fullscreen."""
        # Handled at render time — if zoomed, only render focused pane
        if self.root:
            node = self._find_node(self._focus_id)
            if node:
                node.zoomed = not node.zoomed

    def compute(self, width: int, height: int) -> dict[str, Rect]:
        """Compute screen rectangles for all panes."""
        if not self.root:
            return {}

        # Check for zoomed pane
        zoomed_node = self._find_zoomed()
        if zoomed_node:
            return {zoomed_node.module_id: Rect(0, 0, width, height)}

        rects = {}
        self._compute_recursive(self.root, Rect(0, 0, width, height), rects)
        return rects

    def _rebuild_tree(self):
        """Rebuild tiling tree from pane order."""
        n = len(self._pane_order)
        if n == 0:
            self.root = None
        elif n == 1:
            self.root = TileNode(module_id=self._pane_order[0])
        elif n == 2:
            # Vertical split: left | right
            self.root = TileNode(
                split=SplitDirection.HORIZONTAL, ratio=0.5,
                children=[
                    TileNode(module_id=self._pane_order[0]),
                    TileNode(module_id=self._pane_order[1]),
                ]
            )
        elif n == 3:
            # Master-stack: left master, right stacked
            self.root = TileNode(
                split=SplitDirection.HORIZONTAL, ratio=0.5,
                children=[
                    TileNode(module_id=self._pane_order[0]),
                    TileNode(
                        split=SplitDirection.VERTICAL, ratio=0.5,
                        children=[
                            TileNode(module_id=self._pane_order[1]),
                            TileNode(module_id=self._pane_order[2]),
                        ]
                    ),
                ]
            )
        elif n == 4:
            # 2×2 grid
            self.root = TileNode(
                split=SplitDirection.HORIZONTAL, ratio=0.5,
                children=[
                    TileNode(
                        split=SplitDirection.VERTICAL, ratio=0.5,
                        children=[
                            TileNode(module_id=self._pane_order[0]),
                            TileNode(module_id=self._pane_order[1]),
                        ]
                    ),
                    TileNode(
                        split=SplitDirection.VERTICAL, ratio=0.5,
                        children=[
                            TileNode(module_id=self._pane_order[2]),
                            TileNode(module_id=self._pane_order[3]),
                        ]
                    ),
                ]
            )
        else:
            # Master + stack: first pane is master (left 40%), rest stack right
            rest = self._pane_order[1:]

            # Build stack as nested vertical splits
            if len(rest) == 1:
                right = TileNode(module_id=rest[0])
            else:
                right = self._build_stack(rest)

            self.root = TileNode(
                split=SplitDirection.HORIZONTAL, ratio=0.4,
                children=[
                    TileNode(module_id=self._pane_order[0]),
                    right,
                ]
            )

    def _build_stack(self, ids: list[str]) -> TileNode:
        """Build a vertical stack of panes from a list of module IDs."""
        if len(ids) == 1:
            return TileNode(module_id=ids[0])
        if len(ids) == 2:
            return TileNode(
                split=SplitDirection.VERTICAL, ratio=0.5,
                children=[
                    TileNode(module_id=ids[0]),
                    TileNode(module_id=ids[1]),
                ]
            )
        # Split first off, recurse rest
        ratio = 1.0 / len(ids)
        return TileNode(
            split=SplitDirection.VERTICAL, ratio=ratio,
            children=[
                TileNode(module_id=ids[0]),
                self._build_stack(ids[1:]),
            ]
        )

    def _compute_recursive(self, node: TileNode, rect: Rect, out: dict):
        """Recursively compute rectangles."""
        if node.is_leaf:
            out[node.module_id] = rect
            return

        if node.split == SplitDirection.HORIZONTAL:
            split_x = rect.x + int(rect.w * node.ratio)
            left_rect = Rect(rect.x, rect.y, split_x - rect.x, rect.h)
            right_rect = Rect(split_x, rect.y, rect.w - (split_x - rect.x), rect.h)
            self._compute_recursive(node.children[0], left_rect, out)
            self._compute_recursive(node.children[1], right_rect, out)
        else:
            split_y = rect.y + int(rect.h * node.ratio)
            top_rect = Rect(rect.x, rect.y, rect.w, split_y - rect.y)
            bot_rect = Rect(rect.x, split_y, rect.w, rect.h - (split_y - rect.y))
            self._compute_recursive(node.children[0], top_rect, out)
            self._compute_recursive(node.children[1], bot_rect, out)

    def _find_node(self, module_id: str) -> Optional[TileNode]:
        """Find a leaf node by module ID."""
        return self._find_recursive(self.root, module_id)

    def _find_recursive(self, node: Optional[TileNode], module_id: str) -> Optional[TileNode]:
        if node is None:
            return None
        if node.is_leaf and node.module_id == module_id:
            return node
        for child in node.children:
            found = self._find_recursive(child, module_id)
            if found:
                return found
        return None

    def _find_zoomed(self) -> Optional[TileNode]:
        """Find a zoomed leaf node."""
        return self._find_zoomed_recursive(self.root)

    def _find_zoomed_recursive(self, node: Optional[TileNode]) -> Optional[TileNode]:
        if node is None:
            return None
        if node.is_leaf and node.zoomed:
            return node
        for child in node.children:
            found = self._find_zoomed_recursive(child)
            if found:
                return found
        return None

    def debug_layout(self, width: int, height: int) -> str:
        """ASCII visualization of current layout for debugging."""
        rects = self.compute(width, height)
        if not rects:
            return "[empty]"
        lines = []
        for mid, r in rects.items():
            focused = " *" if mid == self._focus_id else ""
            lines.append(f"  {mid:<24} → ({r.x},{r.y}) {r.w}×{r.h}{focused}")
        return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    layout = TilingLayout()
    W, H = 120, 40

    print("═══ TILING ENGINE DEMO ═══\n")

    for mod in ["status.pipboy", "tools.music", "pro.hacking", "tools.animation"]:
        layout.add(mod)
        print(f"After adding {mod} ({layout.pane_count} panes):")
        print(layout.debug_layout(W, H))
        print()

    print("Focus cycling:")
    for _ in range(5):
        layout.focus_next()
        print(f"  Focused: {layout.focused_id}")

    print("\nRemove tools.music:")
    layout.remove("tools.music")
    print(layout.debug_layout(W, H))

    print("\nAdd 2 more:")
    layout.add("stem.chemistry")
    layout.add("pro.softdev")
    print(layout.debug_layout(W, H))
