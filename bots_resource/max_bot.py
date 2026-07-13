"""
max_bot (resource): 0/1-knapsack DP + race-aware item filtering +
nearest-neighbour route repair.

Strategy flow every turn:
  1. Filter out items another bot will almost certainly grab first
     (they're strictly closer, or equally close but ID-ahead).
  2. Still-available items enter a 0/1 knapsack DP over the remaining
     move budget — this picks the *set* of items with the best total
     value we can afford (treating each item's cost as Manhattan
     distance from where we stand *right now*).
  3. The DP assumes costs are independent, which they aren't — visiting
     A first changes the cost to B.  A budget-aware nearest-neighbour
     walk over the DP's chosen set repairs that blind spot, dropping
     anything that becomes unaffordable when real travel order is
     accounted for.
  4. Take one step toward the first surviving item.  Next turn the
     whole thing starts fresh, so "just one step" is all we need.

Items the opponent is likely to grab are dropped early: chasing a
pickup we can't win wastes budget we could spend on something real.
"""
from engine.bot import Bot, Move


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if abs(dx) >= abs(dy):
        if dx > 0: return Move.RIGHT
        if dx < 0: return Move.LEFT
        if dy > 0: return Move.DOWN
        if dy < 0: return Move.UP
    else:
        if dy > 0: return Move.DOWN
        if dy < 0: return Move.UP
        if dx > 0: return Move.RIGHT
        if dx < 0: return Move.LEFT
    return Move.UP


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _winnable_selector(state):
    """Return items we have a realistic shot at claiming.

    An item is considered winnable unless an opponent is strictly closer,
    or equally close but has the ID tie-break (IDs are sorted alphabetically,
    so 'earlier' IDs win ties in the engine's collection rule).
    """
    me = state.position
    my_id = state.self_id
    others = [(bid, pos) for bid, pos in state.positions.items() if bid != my_id]
    keep = []
    for item in state.items:
        my_dist = _dist(me, item.position)
        beaten = False
        for bid, pos in others:
            opp_dist = _dist(pos, item.position)
            if opp_dist < my_dist or (opp_dist == my_dist and bid < my_id):
                beaten = True
                break
        if not beaten:
            keep.append(item)
    return keep


def _knapsack_plan(state, candidates):
    """0/1 knapsack DP over candidate items, then budget-aware routing.

    Returns the first target position to step toward, or None.
    """
    capacity = state.moves_left
    items_with_cost = [(it, _dist(state.position, it.position)) for it in candidates]
    items_with_cost = [(it, c) for it, c in items_with_cost if 0 < c <= capacity]
    if not items_with_cost:
        return None

    # DP: dp[c] = max value achievable with exactly c moves
    dp = [0] * (capacity + 1)
    keep = [None] * len(items_with_cost)

    for i, (item, cost) in enumerate(items_with_cost):
        row = bytearray(capacity + 1)
        for c in range(capacity, cost - 1, -1):
            cand = dp[c - cost] + item.value
            if cand > dp[c]:
                dp[c] = cand
                row[c] = 1
        keep[i] = row

    # Reconstruct selected set
    selected = []
    c = capacity
    for i in range(len(items_with_cost) - 1, -1, -1):
        if keep[i][c]:
            item, cost = items_with_cost[i]
            selected.append(item)
            c -= cost

    if not selected:
        return None

    # Budget-aware route repair (nearest-neighbour)
    current = state.position
    remaining = capacity
    for _ in range(len(selected)):
        reachable = [it for it in selected if _dist(current, it.position) <= remaining]
        if not reachable:
            break
        nxt = min(reachable, key=lambda it: _dist(current, it.position))
        remaining -= _dist(current, nxt.position)
        current = nxt.position
        selected.remove(nxt)
        return current  # return IMMEDIATELY after picking first target

    return None


class MaxBot(Bot):
    def decide(self, state) -> Move:
        if not state.items or state.moves_left <= 0:
            return Move.UP

        winnable = _winnable_selector(state)
        pool = winnable if winnable else list(state.items)

        target = _knapsack_plan(state, pool)
        if target is None:
            return Move.UP

        return _step_toward(state.position, target)
