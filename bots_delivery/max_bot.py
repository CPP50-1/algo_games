"""
max_bot (delivery): picks the best unclaimed job by rate (value/travel_time)
via a priority queue, then takes one step toward its pickup.

When carrying, heads straight for the dropoff.  Jobs that can't meet
their deadline even by going straight there are dropped before ranking.

Movement uses the larger‑gap‑first heuristic (moves on the axis with
the biggest remaining distance), which is slightly more natural than
always favouring x first.
"""

from engine.bot import Bot, Move
import heapq


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if abs(dx) >= abs(dy):
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
        if dy > 0:
            return Move.DOWN
        if dy < 0:
            return Move.UP
    else:
        if dy > 0:
            return Move.DOWN
        if dy < 0:
            return Move.UP
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
    return Move.UP


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _best_job(state):
    heap = []
    for job in state.jobs:
        if job.claimed_by is not None:
            continue
        to_pickup = _dist(state.position, job.pickup)
        leg = _dist(job.pickup, job.dropoff)
        travel = to_pickup + leg
        slack = job.deadline - (state.turn + travel)
        if slack < 0:
            continue
        rate = job.value / travel if travel > 0 else float(job.value)
        heapq.heappush(heap, (-rate, slack, job.id, job))
    return heap[0][3] if heap else None


class MaxBot(Bot):
    def decide(self, state) -> Move:
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        target = _best_job(state)
        if target is None:
            return Move.UP

        return _step_toward(state.position, target.pickup)
