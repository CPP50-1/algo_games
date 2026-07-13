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
from games.resource import ResourceView, Item

_state : ResourceView = None

def knapsack_recurse(w, values, weights, n, memo, state_items) -> tuple[int, list[int]]:
    #print(f"recurse n={n} w={w} weights: {weights}; values: {values}",file=sys.stderr, flush=True)

    if n==0 or w==0:
        return 0, [] # (0, -1)
    if memo[n][w][0] != -1:
       return memo[n][w] # already calculated

    pick_indices = []
    pick = 0
    if weights[n-1] <= w:
        # could go into the knapsack
        pick_position = state_items[n-1].position
        pick_weights = [distance(it.position, pick_position) for it in state_items]
        v, pick_indices = knapsack_recurse(w - weights[n-1], values, pick_weights, n-1, memo, state_items)
        pick = values[n-1] + v

    no_pick, no_pick_indices = knapsack_recurse(w, values, weights, n-1, memo, state_items)
    if pick > no_pick:
        # Best it to puck
        #pick_indices.append(n-1)
        #print(f"Adding pick {pick} n={n} w={w} indices={pick_indices}",file=sys.stderr, flush=True)
        memo[n][w] = (pick, pick_indices + [n-1])
    else:
        #no_pick_indices.append(n-1)
        #print(f"Adding nopick {no_pick} n={n} w={w} indices={no_pick_indices}",file=sys.stderr, flush=True)
        memo[n][w] = (no_pick, no_pick_indices)
    return memo[n][w]

def knapsack(w, values, weights, state_items) -> tuple[int, list[int]]:
    n = len(values)
    # init memoization table (we memo the pairs (value, index))
    memo =[ [(-1,[]) for _ in range (w+1)] for _ in range(n+1) ] #[[(-1,0)] * (w+1) for _ in range(n+1)]
    #print(f"knapsack memo={memo}", file=sys.stderr, flush=True)

    return knapsack_recurse(w, values, weights, n, memo, state_items)



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
    return Move.UP

def distance(position1, position2):
    return abs(position1[0] - position2[0]) + abs(position1[1] - position2[1])


class AlainResourceBot(Bot):
    def decide(self, state) -> Move:
        global _state
        if not state.items:
            return Move.UP  # nothing left to do -- direction is irrelevant

        _state = state
        weights = list(map(lambda it: distance(it.position, state.position), state.items))
        values = list(map(lambda it: it.value, state.items))
        #print(f"w={state.moves_left} weights: {weights}; values: {values}", file=sys.stderr, flush=True)

        value, indices= knapsack(state.moves_left, values, weights, state.items)

        selected_item = min([state.items[i] for i in indices], key=lambda it: distance(state.position, it.position))
        selected_item_distance = distance(selected_item.position, state.position)
        selected_items = [state.items[i] for i in indices]
        print(f"w={state.moves_left} my_pos={state.position} weights: {weights}; values: {values} => {value}\n => pick closest from ({selected_items}): {selected_item} at {selected_item_distance}\n", file=sys.stderr, flush=True)
        #selected_position = state.items[indices[0]].position
        return _step_toward(state.position, selected_item.position)


if __name__ == "__main__":
    s = ResourceView(self_id='alain_resource_bot', width=21, height=21, turn=0, position=(7, 20), moves_left=40,
                 score={'alain_resource_bot': 0, 'example_resource_bot': 0},
                 items=[Item(id='item0', position=(0, 0), value=10), Item(id='item1', position=(12, 8), value=47),
                        Item(id='item2', position=(4, 16), value=84), Item(id='item3', position=(17, 3), value=31),
                        Item(id='item4', position=(9, 11), value=68), Item(id='item5', position=(1, 19), value=15),
                        Item(id='item6', position=(14, 6), value=52), Item(id='item7', position=(6, 14), value=89),
                        Item(id='item8', position=(19, 1), value=36), Item(id='item9', position=(11, 9), value=73),
                        Item(id='item10', position=(3, 17), value=20), Item(id='item11', position=(16, 4), value=57),
                        Item(id='item12', position=(8, 12), value=94), Item(id='item13', position=(0, 20), value=41)],
                 positions={'alain_resource_bot': (7, 20), 'example_resource_bot': (14, 20)})
    bot = AlainResourceBot()
    bot.decide(s)
