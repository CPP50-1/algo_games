"""Reference bot for the delivery game -- shows the minimum needed to
implement the Bot API against a DeliveryView.

Strategy: always head for the nearest unclaimed job's pickup cell (or
your own dropoff if you're already carrying something). This ignores
deadlines completely -- it's the naive "closest first" trap this game
module is built to expose. Trainees should be able to beat it easily by
weighing urgency (deadline minus time-to-reach) alongside distance,
e.g. with a small heapq of candidate jobs re-ranked every turn.
"""
from engine.bot import Bot, Move


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if dx > 0:
        return Move.RIGHT
    if dx < 0:
        return Move.LEFT
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    return Move.UP  # already there -- direction doesn't matter this turn


class ExampleDeliveryBot(Bot):
    def decide(self, state) -> Move:
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        available = [j for j in state.jobs if j.claimed_by is None]
        if not available:
            return Move.UP  # nothing to do -- direction is irrelevant

        nearest = min(
            available,
            key=lambda j: abs(j.pickup[0] - state.position[0]) + abs(j.pickup[1] - state.position[1]),
        )
        return _step_toward(state.position, nearest.pickup)
