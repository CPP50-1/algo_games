"""Reference bot for the resource-constrained grid game -- shows the
minimum needed to implement the Bot API against a ResourceView.

Strategy: always walk toward the nearest available item, ignoring your
remaining budget and every other item's value entirely. This is the
naive "closest first" trap the game module is built to expose: it
regularly leaves higher-value items unreachable once the budget runs
out, when a bot that reasoned about which *combination* of items fits
the remaining budget (i.e. treated this as a knapsack problem) would
have scored more. Trainees should be able to beat this by, roughly:
estimate the cost to reach each remaining item, then solve (or
approximate) 0/1 knapsack over (item, cost, value) with capacity =
moves_left, instead of always taking the cheapest single step.
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
    return Move.UP


class SecondExampleResourceBot(Bot):
    def decide(self, state) -> Move:
        if not state.items:
            return Move.UP  # nothing left to do -- direction is irrelevant

        nearest = min(
            state.items,
            key=lambda it: abs(it.position[0] - state.position[0]) + abs(it.position[1] - state.position[1]),
        )
        return _step_toward(state.position, nearest.position)
