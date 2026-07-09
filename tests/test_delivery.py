"""Unit tests for games.delivery -- checks the scheduling mechanics
themselves, independent of any bot's strategy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.bot import Move
from games.delivery import DeliveryGame, _generate_jobs


def test_schedule_is_deterministic():
    a = _generate_jobs(width=20, height=20, num_jobs=10, spawn_every=5)
    b = _generate_jobs(width=20, height=20, num_jobs=10, spawn_every=5)
    assert a == b


def test_setup_is_deterministic():
    g1, g2 = DeliveryGame(width=20, height=20, num_jobs=5), DeliveryGame(width=20, height=20, num_jobs=5)
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


def test_pickup_and_delivery_scores_points():
    g = DeliveryGame(width=20, height=20, num_jobs=1, spawn_every=1, max_turns=50)
    g.setup(["a", "b"])
    job = g._schedule[0]

    # Put "a" one step away from the pickup cell and walk it on. "b"
    # stays parked in a corner well out of the way.
    px, py = job.pickup
    g._positions["a"] = (px, py + 1) if py + 1 < g.height else (px, py - 1)
    g._positions["b"] = (g.width - 1, g.height - 1)

    g.step({"a": _move_toward(g._positions["a"], job.pickup), "b": Move.UP})
    assert g._positions["a"] == job.pickup
    assert g._carrying["a"] == job.id

    # Now walk it from the pickup cell to the dropoff cell, one step per
    # turn, until it lands exactly on the dropoff and delivers.
    for _ in range(2 * (g.width + g.height)):
        if g._carrying["a"] is None:
            break
        move = _move_toward(g._positions["a"], job.dropoff)
        g.step({"a": move, "b": Move.UP})

    assert g._score["a"] == job.value
    assert g._carrying["a"] is None


def test_missed_deadline_expires_with_no_payout():
    g = DeliveryGame(width=20, height=20, num_jobs=1, spawn_every=1, max_turns=100)
    g.setup(["a", "b"])
    job = g._schedule[0]

    # Never touch the job; just run past its deadline.
    for _ in range(job.deadline + 2):
        g.step({"a": Move.UP, "b": Move.UP})

    assert job.id not in g._active_job_ids
    assert g._score["a"] == 0
    assert g._score["b"] == 0


def test_simultaneous_claim_is_broken_deterministically():
    g = DeliveryGame(width=20, height=20, num_jobs=1, spawn_every=1, max_turns=50)
    g.setup(["a", "b"])
    job = g._schedule[0]
    px, py = job.pickup
    approach = (px, py + 1) if py + 1 < g.height else (px, py - 1)

    g._positions["a"] = approach
    g._positions["b"] = approach
    move = _move_toward(approach, job.pickup)
    g.step({"a": move, "b": move})

    carriers = [b for b in ("a", "b") if g._carrying[b] == job.id]
    assert carriers == ["a"]  # lexicographically first bot id wins the tie


def test_bots_never_die_in_this_game():
    g = DeliveryGame(width=5, height=5, num_jobs=1, max_turns=10)
    g.setup(["a", "b"])
    for _ in range(10):
        g.step({"a": Move.LEFT, "b": Move.LEFT})  # walk repeatedly into the edge
    assert set(g.alive_bots()) == {"a", "b"}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK: {name}")
