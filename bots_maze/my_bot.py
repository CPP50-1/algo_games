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
from heapq import heappush, heappop
from engine.bot import Bot, Move


class MyBot(Bot):

    def search(self, position, goal, terrain, width, height) -> Move | None:
        # (total_cost, position)
        pq = [(0, position)]

        # Best known cost to each cell
        cost = {position: 0}

        # Parent pointers for reconstructing the path
        parent = {}

        while pq:
            current_cost, current = heappop(pq)

            if current == goal:
                break

            # Ignore outdated queue entries
            if current_cost > cost[current]:
                continue

            x, y = current

            for move in Move:
                nx = x + move.dx
                ny = y + move.dy

                if not (0 <= nx < width and 0 <= ny < height):
                    continue

                next_pos = (nx, ny)

                # Cost of entering the next cell
                new_cost = current_cost + terrain[ny][nx]

                if next_pos not in cost or new_cost < cost[next_pos]:
                    cost[next_pos] = new_cost
                    parent[next_pos] = current
                    heappush(pq, (new_cost, next_pos))

        if goal not in parent and goal != position:
            return None

        # Reconstruct path backwards until we reach the first step
        current = goal
        while parent.get(current) != position:
            if current == position:
                return None
            current = parent[current]

        dx = current[0] - position[0]
        dy = current[1] - position[1]

        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move

        return None

    def decide(self, state) -> Move:
        move = self.search(
            state.position,
            state.goal,
            state.terrain,
            state.width,
            state.height,
        )

        return move if move is not None else Move.UP
