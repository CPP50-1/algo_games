"""Unit tests for games.maze -- checks the weighted-terrain mechanics
themselves, independent of any bot's strategy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bot import Move
from games.maze import MazeGame, _generate_terrain


def _race(width, height, band_cost, moves_sequence):
    g = MazeGame(width=width, height=height, band_cost=band_cost, max_turns=500)
    g.setup(["a"])
    idx = 0
    while not g.is_over():
        alive = g.alive_bots()
        moves = {}
        if "a" in alive:
            if idx >= len(moves_sequence):
                break
            moves["a"] = moves_sequence[idx]
            idx += 1
        g.step(moves)
    return g._turn, g.winners()


def test_terrain_is_deterministic():
    a = _generate_terrain(21, 15, 5)
    b = _generate_terrain(21, 15, 5)
    assert a == b


def test_setup_is_deterministic():
    g1, g2 = MazeGame(), MazeGame()
    g1.setup(["a", "b"])
    g2.setup(["a", "b"])
    assert g1.frame()["positions"] == g2.frame()["positions"]


def test_entering_expensive_terrain_locks_movement():
    g = MazeGame(width=21, height=15, band_cost=5)
    g.setup(["a"])
    # Band A starts at x=5 (see _generate_terrain); the start row (y=7)
    # is within its cost rows (gap is only near the top), so the 5th
    # step right lands exactly on the first expensive cell.
    for _ in range(5):
        g.step({"a": Move.RIGHT})
    pos = g.frame()["positions"]["a"]
    assert pos[0] == 5
    assert "a" not in g.alive_bots()


def test_neither_naive_single_direction_detour_beats_real_path_planning():
    """The whole point of this game module: with two offset cost-bands
    (one open near the top, one open near the bottom), there's no
    single fixed detour direction that's optimal. Going straight is
    worst; detouring only up or only down tie with each other (each
    avoids one band but walks straight through the other); only a route
    that actually threads both gaps beats them both.
    """
    straight, _ = _race(21, 15, 5, [Move.RIGHT] * 20)
    up_only, _ = _race(21, 15, 5, [Move.UP] * 7 + [Move.RIGHT] * 20 + [Move.DOWN] * 7)
    down_only, _ = _race(21, 15, 5, [Move.DOWN] * 7 + [Move.RIGHT] * 20 + [Move.UP] * 7)
    s_curve, _ = _race(
        21, 15, 5, [Move.UP] * 7 + [Move.RIGHT] * 11 + [Move.DOWN] * 10 + [Move.RIGHT] * 9 + [Move.UP] * 3
    )

    assert up_only == down_only  # symmetric bands -> neither fixed direction wins
    assert up_only < straight    # a single detour still beats tunnelling through both
    assert s_curve < up_only     # but only threading both gaps is actually optimal


def test_first_to_reach_goal_wins_and_ends_the_race():
    g = MazeGame(width=6, height=3, band_cost=1, max_turns=50)  # no expensive terrain -- pure race
    g.setup(["a", "b"])
    for _ in range(5):
        if g.is_over():
            break
        moves = {}
        if "a" in g.alive_bots():
            moves["a"] = Move.RIGHT
        if "b" in g.alive_bots():
            moves["b"] = Move.LEFT  # walks into the edge, wasting turns
        g.step(moves)
    assert g.is_over()
    assert g.winners() == ["a"]


def test_walking_into_the_edge_is_a_free_no_op():
    g = MazeGame(width=5, height=5, band_cost=3)
    g.setup(["a"])
    g._positions["a"] = (0, 2)
    g.step({"a": Move.LEFT})  # off the left edge
    assert g._positions["a"] == (0, 2)
    assert "a" in g.alive_bots()  # no lock incurred, free to act again immediately


def test_forfeit_wastes_a_turn_without_locking():
    g = MazeGame(width=5, height=5, band_cost=3)
    g.setup(["a"])
    start = g._positions["a"]
    g.step({"a": None})
    assert g._positions["a"] == start
    assert "a" in g.alive_bots()


def test_nobody_finishing_in_time_is_a_draw():
    g = MazeGame(width=21, height=15, band_cost=5, max_turns=3)
    g.setup(["a"])
    for _ in range(3):
        g.step({"a": Move.UP})  # never heads toward the goal
    assert g.is_over()
    assert g.winners() == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK: {name}")