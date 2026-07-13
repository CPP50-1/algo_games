"""
max_bot (maze): Dijkstra on weighted terrain.
1. Run Dijkstra (priority-queue BFS) from current cell to the goal.
   Each cell has a terrain cost — Dijkstra minimises total weight
   (not step count).
2. The search returns the first step of the cheapest path found.
3. Convert that step to a Move and return it.
4. Re-run every turn: the board is static but your position moves,
   so the optimal path evolves as you progress.
"""
from engine.bot import Bot, Move
import heapq


def _dijkstra_next_step(position, goal, width, height, terrain):
    if position == goal:
        return None

    visited = set()
    pq = [(0, position, None)]

    while pq:
        cost, (x, y), first_step = heapq.heappop(pq)
        if (x, y) in visited:
            continue
        visited.add((x, y))

        if (x, y) == goal:
            return first_step

        for move in Move:
            nx, ny = x + move.dx, y + move.dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if (nx, ny) in visited:
                continue
            step_cost = terrain[ny][nx]
            step = first_step if first_step is not None else (nx, ny)
            heapq.heappush(pq, (cost + step_cost, (nx, ny), step))

    return None


class MaxBot(Bot):
    def decide(self, state) -> Move:
        target = _dijkstra_next_step(
            state.position, state.goal, state.width, state.height, state.terrain
        )
        if target is None:
            return Move.UP

        dx, dy = target[0] - state.position[0], target[1] - state.position[1]
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
        return Move.UP
