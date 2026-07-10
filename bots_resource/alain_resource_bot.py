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
import sys

from engine.bot import Bot, Move

def knapsack_recurse(w, values, weights, n, memo) -> tuple[int,int]:
    if n==0 or w==0:
        return 0
    elif memo[n][w] != -1:
       return memo[n][w] # already calculated
    else:
        if weights[n-1] <= w:
            # could go into the knapsack
            pick = values[n-1] + knapsack_recurse(w - weights[n-1], values, weights, n-1, memo)
        else:
            pick = 0
        no_pick = knapsack_recurse(w, values, weights, n-1, memo)

        memo[n][w] = (max(no_pick, pick), n)
        return memo[n][w]

def knapsack(w, values, weights) -> tuple[int, int]:
    n = len(values)
    # init memoization table (we memo the pairs (value, index))
    memo = [[(-1,0)] * (w+1) for _ in range(n+1)]
    return knapsack_recurse(w, values, weights, n, memo)


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

def distance(position1, position2):
    return abs(position1[0] - position2[0]) + abs(position1[1] - position2[1])


class AlainResourceBot(Bot):
    def decide(self, state) -> Move:
        if not state.items:
            return Move.UP  # nothing left to do -- direction is irrelevant

        weights = list(map(lambda it: distance(it.position, state.position), state.items))
        values = list(map(lambda it: it.value, state.items))
        print(f"weights: {weights}; values: {values}", file=sys.stderr, flush=True)

        value, index = knapsack(state.moves_left, values, weights)
        print(f"w={state.moves_left} weights: {weights}; values: {values} => pick {(value,state.items[index].position)}", file=sys.stderr, flush=True)
        return _step_toward(state.position, state.items[index].position)
