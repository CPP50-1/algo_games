"""Reference bot for the delivery game -- shows the minimum needed to
implement the Bot API against a DeliveryView.

Strategy: always head for the nearest unclaimed job's pickup cell (or
your own dropoff if you're already carrying something). This ignores
deadlines completely -- it's the naive "closest first" trap this game
module is built to expose. Trainees should be able to beat it easily by
weighing urgency (deadline minus time-to-reach) alongside distance,
e.g. with a small heapq of candidate jobs re-ranked every turn.
"""
import sys
from heapq import nlargest

from engine.bot import Bot, Move


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if abs(dx) > abs(dy):
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
    else:
        if dy > 0:
            return Move.DOWN
        if dy < 0:
            return Move.UP
    return Move.UP  # already there -- direction doesn't matter this turn


def distance(position1, position2):
    return abs(position1[0] - position2[0]) + abs(position1[1] - position2[1])


class AlainDelivery(Bot):

    def decide(self, state) -> Move:

        def roi(j):
            cost = distance(state.position, j.pickup) + distance(j.pickup, j.dropoff)
            if cost > j.deadline - state.turn: # Not enough turn to pickup and dropoff
                return 0
            # Heuristic: the closest the drop-off is to the center, the better for the next pickup => ponder the value by its distance to the center
            value = (j.value - distance(j.dropoff, (state.width//2, state.height//2)) // 4) / cost # value per turn
            #print(f"turn: {state.turn} pos:{j.pickup} cost: {cost}: deadline: {j.deadline} value: {j.value} => roi: {value}", file=sys.stderr, flush=True)
            return value

        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        available = [j for j in state.jobs if j.claimed_by is None]

        if not available:
            return _step_toward(state.position, (state.width//2, state.height//2)) # nothing to do -- move towards the center

        best_rois = nlargest(1,
                               map(lambda j: (roi(j), j.pickup), available),
                               key=lambda x: x[0])

        if best_rois[0][0] > 0:
            return _step_toward(state.position, best_rois[0][1] )
        else:
            return _step_toward(state.position, (state.width//2, state.height//2))

