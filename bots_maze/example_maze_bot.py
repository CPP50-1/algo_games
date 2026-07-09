"""Reference bot for the maze race -- shows the minimum needed to
implement the Bot API against a MazeView.

Strategy: plain breadth-first search over the grid, treating every cell
transition as cost 1 and completely ignoring the `terrain` weights. This
finds the path with the fewest cells, which is exactly wrong the moment
terrain costs vary -- on the default map this bot confidently walks
straight through the expensive band because it "looks" shortest, and
loses to anything that instead finds the shortest path *by weight*
(Dijkstra, or A* with an admissible heuristic).
"""
from collections import deque

from engine.bot import Bot, Move


def _bfs_next_step(position, goal, width, height):
    """Returns the next cell to move to along an unweighted shortest
    path, or None if already at the goal (or no path exists, which
    can't happen on this map since there are no impassable cells)."""
    if position == goal:
        return None

    visited = {position}
    queue = deque([(position, None)])  # (cell, first_step_taken_to_get_here)

    while queue:
        (x, y), first_step = queue.popleft()
        for move in Move:
            nx, ny = x + move.dx, y + move.dy
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in visited:
                continue
            visited.add((nx, ny))
            step = first_step if first_step is not None else (nx, ny)
            if (nx, ny) == goal:
                return step
            queue.append(((nx, ny), step))
    return None


class ExampleMazeBot(Bot):
    def decide(self, state) -> Move:
        target = _bfs_next_step(state.position, state.goal, state.width, state.height)
        if target is None:
            return Move.UP

        dx, dy = target[0] - state.position[0], target[1] - state.position[1]
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
        return Move.UP
