"""Unit tests for core.tiling — pure layout-tree logic.

Standard-library only (dataclasses, enum, typing). No TUI runtime needed.
"""

from core.tiling import Rect, SplitDirection, TilingLayout


def _total_area(rects):
    return sum(r.w * r.h for r in rects.values())


# ── pane bookkeeping ─────────────────────────────────────────────

def test_empty_layout_computes_no_rects():
    assert TilingLayout().compute(120, 40) == {}


def test_add_sets_focus_and_count():
    layout = TilingLayout()
    layout.add("a")
    assert layout.pane_count == 1
    assert layout.focused_id == "a"


def test_add_duplicate_is_idempotent_but_refocuses():
    layout = TilingLayout()
    layout.add("a")
    layout.add("b")
    layout.add("a")  # already present
    assert layout.pane_count == 2
    assert layout.focused_id == "a"


def test_remove_unknown_pane_is_noop():
    layout = TilingLayout()
    layout.add("a")
    layout.remove("ghost")
    assert layout.pane_count == 1


def test_remove_focused_pane_refocuses_to_last_remaining():
    layout = TilingLayout()
    layout.add("a")
    layout.add("b")
    layout.remove("b")
    assert layout.focused_id == "a"
    layout.remove("a")
    assert layout.focused_id is None


# ── layout geometry ──────────────────────────────────────────────

def test_single_pane_is_fullscreen():
    layout = TilingLayout()
    layout.add("solo")
    rects = layout.compute(100, 50)
    assert rects == {"solo": Rect(0, 0, 100, 50)}


def test_two_panes_split_horizontally_50_50():
    layout = TilingLayout()
    layout.add("left")
    layout.add("right")
    rects = layout.compute(100, 40)
    assert rects["left"] == Rect(0, 0, 50, 40)
    assert rects["right"] == Rect(50, 0, 50, 40)


def test_layouts_tile_full_area_without_overlap():
    # For 1..6 panes the union of rects covers the whole screen exactly
    # (integer split rounding is absorbed by the complementary halves).
    for count in range(1, 7):
        layout = TilingLayout()
        for i in range(count):
            layout.add(f"m{i}")
        rects = layout.compute(120, 48)
        assert len(rects) == count
        assert _total_area(rects) == 120 * 48


def test_root_split_direction_for_two_panes_is_horizontal():
    layout = TilingLayout()
    layout.add("a")
    layout.add("b")
    assert layout.root is not None
    assert layout.root.split == SplitDirection.HORIZONTAL


# ── focus cycling ────────────────────────────────────────────────

def test_focus_next_wraps_around():
    layout = TilingLayout()
    for name in ("a", "b", "c"):
        layout.add(name)
    # Focus currently on the last-added "c"; next wraps to "a".
    layout.focus_next()
    assert layout.focused_id == "a"


def test_focus_prev_wraps_around():
    layout = TilingLayout()
    for name in ("a", "b", "c"):
        layout.add(name)
    layout.focus_prev()
    assert layout.focused_id == "b"


def test_focus_cycling_on_empty_layout_is_safe():
    layout = TilingLayout()
    layout.focus_next()
    layout.focus_prev()
    assert layout.focused_id is None


# ── swapping and zoom ────────────────────────────────────────────

def test_swap_with_next_reorders_panes():
    layout = TilingLayout()
    for name in ("a", "b", "c"):
        layout.add(name)
    layout.add("a")  # refocus master
    layout.swap_with_next()
    # "a" and "b" exchange positions in the insertion order.
    assert layout._pane_order[:2] == ["b", "a"]


def test_toggle_zoom_makes_focused_pane_fullscreen():
    layout = TilingLayout()
    layout.add("a")
    layout.add("b")
    layout.add("a")  # focus master "a"
    layout.toggle_zoom()
    rects = layout.compute(80, 24)
    # When zoomed, only the focused pane is rendered, full-screen.
    assert rects == {"a": Rect(0, 0, 80, 24)}
