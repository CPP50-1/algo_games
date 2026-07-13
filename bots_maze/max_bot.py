"""
max_bot (maze): Dijkstra on weighted terrain, recomputed every turn.

Why weight: moving into a cell costs its terrain value in turns, not
just one.  BFS (hop count) would walk straight through an expensive
band because it *looks* shorter even when it's clearly slower.
Dijkstra with edge weight = destination cell's terrain cost finds the
path that minimises total turns, which naturally detours around
expensive cells when it saves time.
"""
from engine.bot import Bot, Move
import heapq

# Lookup: delta position → Move
_DELTA_MOVE = {
    (1, 0): Move.RIGHT,
    (-1, 0): Move.LEFT,
    (0, 1): Move.DOWN,
    (0, -1): Move.UP,
}


def _dijkstra_next_step(position, goal, terrain, width, height):
    if position == goal:
        return None

    visited = set()
    pq = [(0, position, None)]

    while pq:
        cost, cur, first_step = heapq.heappop(pq)
        if cur in visited:
            continue
        visited.add(cur)

        if cur == goal:
            return first_step

        cx, cy = cur
        for mov in Move:
            nx, ny = cx + mov.dx, cy + mov.dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            nxt = (nx, ny)
            if nxt in visited:
                continue
            step = first_step if first_step is not None else nxt
            heapq.heappush(pq, (cost + terrain[ny][nx], nxt, step))

    return None


class MaxBot(Bot):
    def decide(self, state) -> Move:
        target = _dijkstra_next_step(
            state.position, state.goal, state.terrain, state.width, state.height,
        )
        if target is None:
            return Move.UP

        dx = target[0] - state.position[0]
        dy = target[1] - state.position[1]
        return _DELTA_MOVE.get((dx, dy), Move.UP)
