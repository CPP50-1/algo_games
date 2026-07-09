"""Unit tests for games.tron -- checks the rules themselves are correct
and deterministic, independent of any bot's strategy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bot import Move
from games.tron import TronGame


def test_setup_is_deterministic():
    g1, g2 = TronGame(width=21, height=21), TronGame(width=21, height=21)
    g1.setup(["a", "b"])
    g2.setup(["a", "b"])
    assert g1.frame() == g2.frame()


def test_wall_collision_kills():
    g = TronGame(width=10, height=10)
    g.setup(["a", "b"])
    facing_a = g._facing["a"]
    opposite = {Move.RIGHT: Move.LEFT, Move.LEFT: Move.RIGHT, Move.UP: Move.DOWN, Move.DOWN: Move.UP}[facing_a]
    # Step forward once to lay a trail cell behind "a", then reverse into it.
    g.step({"a": facing_a, "b": g._facing["b"]})
    assert "a" in g.alive_bots()
    g.step({"a": opposite, "b": g._facing["b"]})
    assert "a" not in g.alive_bots()


def test_out_of_bounds_kills():
    g = TronGame(width=5, height=5)
    g.setup(["a", "b"])
    # Drive "a" left off the edge of a tiny board.
    for _ in range(10):
        if "a" not in g.alive_bots():
            break
        g.step({"a": Move.LEFT, "b": Move.UP})
    assert "a" not in g.alive_bots()


def test_head_on_collision_kills_both():
    g = TronGame(width=10, height=10)
    g.setup(["a", "b"])
    # Force both bots to move into the exact same cell.
    pos_a = g.view_for("a").positions["a"]
    pos_b = g.view_for("b").positions["b"]
    target = ((pos_a[0] + pos_b[0]) // 2, (pos_a[1] + pos_b[1]) // 2)
    move_a = Move.RIGHT if target[0] > pos_a[0] else Move.LEFT
    move_b = Move.RIGHT if target[0] > pos_b[0] else Move.LEFT
    # Walk both bots toward the midpoint until they collide or one dies.
    for _ in range(g.width):
        alive = g.alive_bots()
        if len(alive) < 2:
            break
        g.step({"a": move_a, "b": move_b})
    assert g.is_over()


def test_last_bot_alive_wins():
    g = TronGame(width=6, height=6)
    g.setup(["a", "b"])
    # Force a controlled scenario: "a" one step from the left edge, "b"
    # safely in the middle with room to keep moving.
    g._positions = {"a": (0, 0), "b": (3, 3)}
    g._walls = {(0, 0), (3, 3)}
    g._facing = {"a": Move.LEFT, "b": Move.UP}
    g._alive = ["a", "b"]

    g.step({"a": Move.LEFT, "b": Move.UP})  # "a" walks off the left edge

    assert g.is_over()
    assert g.winners() == ["b"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK: {name}")
