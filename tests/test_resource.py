"""Unit tests for games.resource -- checks the collection/budget
mechanics themselves, independent of any bot's strategy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bot import Move
from games.resource import ResourceGame, _generate_items


def test_layout_is_deterministic():
    a = _generate_items(width=20, height=20, num_items=10)
    b = _generate_items(width=20, height=20, num_items=10)
    assert a == b


def test_setup_is_deterministic():
    g1, g2 = ResourceGame(width=20, height=20, num_items=5), ResourceGame(width=20, height=20, num_items=5)
    g1.setup(["a", "b"])
    g2.setup(["a", "b"])
    assert g1.frame() == g2.frame()


def _move_toward(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx > 0:
        return Move.RIGHT
    if dx < 0:
        return Move.LEFT
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    return Move.UP


def test_collecting_an_item_scores_its_value_and_removes_it():
    g = ResourceGame(width=20, height=20, num_items=1, move_budget=30)
    g.setup(["a", "b"])
    item = g._items_by_id["item0"]
    ix, iy = item.position
    g._positions["a"] = (ix, iy + 1) if iy + 1 < g.height else (ix, iy - 1)
    g._positions["b"] = (0, 0)

    g.step({"a": _move_toward(g._positions["a"], item.position), "b": Move.UP})

    assert g._positions["a"] == item.position
    assert g._score["a"] == item.value
    assert "item0" not in g._available_ids


def test_budget_exhaustion_stops_movement_but_not_the_match():
    g = ResourceGame(width=20, height=20, num_items=1, move_budget=1)
    g.setup(["a", "b"])
    start = g._positions["a"]
    g.step({"a": Move.RIGHT, "b": Move.RIGHT})
    assert g._moves_left["a"] == 0
    moved_position = g._positions["a"]
    # Second step: "a" is out of budget, so it must not move again even
    # though we hand it a move.
    g.step({"a": Move.LEFT, "b": Move.LEFT})
    assert g._positions["a"] == moved_position
    assert start != moved_position or g.width == 1  # sanity: it did move once


def test_match_ends_only_once_every_bot_is_out_of_budget():
    g = ResourceGame(width=20, height=20, num_items=1, move_budget=3)
    g.setup(["a", "b"])
    for _ in range(3):
        assert not g.is_over()
        g.step({"a": Move.UP, "b": Move.UP})
    assert g.is_over()


def test_simultaneous_claim_is_broken_deterministically():
    g = ResourceGame(width=20, height=20, num_items=1, move_budget=10)
    g.setup(["a", "b"])
    item = g._items_by_id["item0"]
    ix, iy = item.position
    approach = (ix, iy + 1) if iy + 1 < g.height else (ix, iy - 1)
    g._positions["a"] = approach
    g._positions["b"] = approach
    move = _move_toward(approach, item.position)
    g.step({"a": move, "b": move})
    assert g._score["a"] == item.value
    assert g._score["b"] == 0


def test_bots_never_die_in_this_game():
    g = ResourceGame(width=5, height=5, num_items=1, move_budget=5)
    g.setup(["a", "b"])
    for _ in range(5):
        g.step({"a": Move.LEFT, "b": Move.LEFT})
    assert not g.alive_bots()  # budget exhausted, but this isn't "death"
    assert g.is_over()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK: {name}")
