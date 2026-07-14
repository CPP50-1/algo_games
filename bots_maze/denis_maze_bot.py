"""Maze-race bot -- Dijkstra shortest path *by weight*, not by cell
count, recomputed fresh from the current position every decide() call.

Why weight and not hop count: moving into a cell of terrain cost N
locks you out for N-1 extra turns on top of the turn you just spent --
so the real "length" of an edge into a cell is that cell's terrain
cost, not 1. A plain BFS (like the reference bot) can't represent that
at all; it only ever sees "neighbour, cost-1-hop", so it happily walks
straight through an expensive band because it *looks* like fewer
cells, even when it's clearly more turns. Dijkstra with edge weight =
destination cell's terrain cost is the direct fix: it finds the path
that minimises total turns, which on this map means detouring around
each band's expensive side through its cheap gap instead of tunnelling
through.

Recomputing every turn (rather than planning once from the start and
blindly following it) costs almost nothing on a board this size, and
means there's no assumption baked in about this bot instance living
for the whole match or the engine calling it in any particular order --
it's always just "shortest weighted path from wherever I am right now
to the goal."
"""
import heapq

from engine.bot import Bot, Move


def _dijkstra_next_step(position, goal, terrain, width, height):
    """Standard Dijkstra over the grid, edge weight = terrain cost of
    the cell being entered. Returns the first step along an optimal
    path, or None if already at the goal.
    """
    if position == goal:
        return None

    dist = {position: 0}
    prev = {}
    visited = set()
    heap = [(0, position)]

    while heap:
        d, cur = heapq.heappop(heap)
        if cur in visited:
            continue  # stale heap entry from before this cell was relaxed to a better distance
        visited.add(cur)
        if cur == goal:
            break

        x, y = cur
        for move in Move:
            nx, ny = x + move.dx, y + move.dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            neighbor = (nx, ny)
            if neighbor in visited:
                continue
            new_dist = d + terrain[ny][nx]  # cost of the cell we'd be entering
            if new_dist < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_dist
                prev[neighbor] = cur
                heapq.heappush(heap, (new_dist, neighbor))

    if goal not in prev:
        return None  # unreachable -- shouldn't happen, there are no impassable cells

    # Walk backward from goal to position, then take the one step next
    # to `position` -- that's all decide() needs to return this turn.
    path = [goal]
    while path[-1] != position:
        path.append(prev[path[-1]])
    path.reverse()
    return path[1]


class DenisMazeBot(Bot):
    def decide(self, state) -> Move:
        target = _dijkstra_next_step(state.position, state.goal, state.terrain, state.width, state.height)
        if target is None:
            return Move.UP  # already at the goal -- direction is irrelevant

        dx, dy = target[0] - state.position[0], target[1] - state.position[1]
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
        return Move.UP