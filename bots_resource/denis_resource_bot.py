"""Resource-constrained grid bot -- solves 0/1 knapsack over the
remaining move budget instead of always walking to the nearest pickup.

Everything below is recomputed from scratch on every decide() call,
because position, budget, and the set of still-available items all
change turn to turn (and other bots can take an item off the table
between our turns):

1. Treat each available item's "weight" as its Manhattan distance from
   wherever we're standing *right now* -- there are no walls, so
   Manhattan distance is exactly the move cost to reach it on its own.
2. Drop items another bot is guaranteed to win the race for (they're
   strictly closer, or tied and ahead of us in the id tie-break used
   by the game's collection rule) -- no point spending knapsack budget
   planning around a pickup we can't actually claim.
3. Solve 0/1 knapsack -- values vs. distances, capacity = moves_left --
   with the standard DP table over "budget remaining -> best achievable
   value" (see _knapsack_select), and reconstruct which items make up
   that optimum.
4. The knapsack step has one blind spot: it assumes every item is
   reached directly from where we stand *now*, but visiting item A
   first changes the real cost of reaching item B afterwards. So the
   DP's selected subset gets walked with a budget-aware
   nearest-neighbour pass (_plan_route), which uses real, order
   dependent travel cost and drops anything that stops being
   affordable once the earlier legs of the trip are paid for.
5. Head one step toward whichever item survives that plan. Since the
   whole thing is re-solved next turn anyway, this only has to be
   right for the very next move -- not the whole match.
"""
from engine.bot import Bot, Move


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    # Whichever axis has the bigger remaining gap moves first -- total
    # distance covered doesn't depend on the order on an open grid,
    # this just avoids always favouring x the way a naive walk would.
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


def _uncontested_items(state):
    """Items where no other still-moving bot is closer, or exactly as
    close but ahead of us in the id tie-break -- items we can't win are
    dead weight in the knapsack, so filter them out before optimising.
    """
    me = state.position
    others = [(bid, pos) for bid, pos in state.positions.items() if bid != state.self_id]
    keep = []
    for item in state.items:
        my_dist = _dist(me, item.position)
        beaten = False
        for bid, pos in others:
            other_dist = _dist(pos, item.position)
            if other_dist < my_dist or (other_dist == my_dist and bid < state.self_id):
                beaten = True
                break
        if not beaten:
            keep.append(item)
    return keep


def _knapsack_select(candidates, capacity):
    """Standard 0/1 knapsack DP: dp[c] = best total value achievable
    with total distance-cost <= c, then walk the choice table backward
    to recover *which* items made up that optimum.

    `candidates` is a list of (item, cost) pairs with
    0 < cost <= capacity already guaranteed by the caller.
    """
    n = len(candidates)
    dp = [0] * (capacity + 1)
    keep = [None] * n  # keep[i][c] == 1 iff item i was added at capacity c

    for i, (item, cost) in enumerate(candidates):
        value = item.value
        row_keep = bytearray(capacity + 1)
        # Descending capacity loop is what makes this 0/1 (each item
        # used at most once) rather than unbounded knapsack.
        for c in range(capacity, cost - 1, -1):
            candidate_value = dp[c - cost] + value
            if candidate_value > dp[c]:
                dp[c] = candidate_value
                row_keep[c] = 1
        keep[i] = row_keep

    selected = []
    c = capacity
    for i in range(n - 1, -1, -1):
        if keep[i][c]:
            item, cost = candidates[i]
            selected.append(item)
            c -= cost
    return selected


def _plan_route(start, items, budget):
    """Budget-aware nearest-neighbour walk over `items`: repeatedly
    step to whichever remaining item is closest, but only among items
    we can still afford given everywhere we've already committed to
    going. This is what covers the knapsack DP's blind spot -- real
    travel cost depends on visiting order, not just distance from the
    start.
    """
    current = start
    remaining_budget = budget
    remaining = list(items)
    route = []
    while remaining:
        reachable = [it for it in remaining if _dist(current, it.position) <= remaining_budget]
        if not reachable:
            break
        nxt = min(reachable, key=lambda it: _dist(current, it.position))
        route.append(nxt)
        remaining_budget -= _dist(current, nxt.position)
        current = nxt.position
        remaining.remove(nxt)
    return route


class ResourceBot(Bot):
    def decide(self, state) -> Move:
        if not state.items or state.moves_left <= 0:
            return Move.UP  # nothing to do, or we're out of budget anyway

        winnable = _uncontested_items(state)
        if not winnable:
            # Nothing looks clearly ours by the race heuristic -- fall
            # back to considering everything rather than sitting idle.
            winnable = list(state.items)

        capacity = state.moves_left
        candidates = [
            (item, _dist(state.position, item.position))
            for item in winnable
        ]
        candidates = [(item, cost) for item, cost in candidates if 0 < cost <= capacity]

        if not candidates:
            return _step_toward(state.position, _nearest(state).position)

        selected = _knapsack_select(candidates, capacity)
        if not selected:
            return _step_toward(state.position, _nearest(state).position)

        route = _plan_route(state.position, selected, capacity)
        if not route:
            return _step_toward(state.position, _nearest(state).position)

        return _step_toward(state.position, route[0].position)


def _nearest(state):
    """Fallback target when our own filtering leaves nothing to aim
    at (e.g. every item looks contested, or none fit the budget by our
    estimate) -- better to head toward the closest item and hope it's
    still there than to stand still.
    """
    return min(state.items, key=lambda it: _dist(state.position, it.position))