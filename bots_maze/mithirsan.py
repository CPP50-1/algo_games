import heapq

from engine.bot import Bot, Move
from games.maze import MazeView, Position, Terrain


def _manhattan(pos: Position, goal: Position) -> int:
    return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])


def _astar_next_step(
    pos: Position,
    goal: Position,
    width: int,
    height: int,
    terrain: Terrain,
):
    if pos == goal:
        return None

    g_score: dict[Position, int] = {pos: 0}
    open_set: list[tuple[int, Position, Position | None]] = [
        (_manhattan(pos, goal), pos, None)
    ]

    while open_set:
        _, current, first_step = heapq.heappop(open_set)
        if current == goal:
            return first_step

        # If we've found a better path to current already, skip
        if current in g_score and _manhattan(current, goal) + g_score[current] < _:
            continue

        for move in Move:
            nx, ny = current[0] + move.dx, current[1] + move.dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue

            neighbor: Position = (nx, ny)
            cost: int = terrain[ny][nx]
            tentative_g = g_score[current] + cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                # Propagate first_step: if current is start, this move is the first step
                heapq.heappush(
                    open_set,
                    (
                        tentative_g + _manhattan(neighbor, goal),
                        neighbor,
                        first_step if first_step is not None else neighbor,
                    ),
                )

    return None


class MithirsanMazeBot(Bot):
    def decide(self, state: MazeView) -> Move:
        target = _astar_next_step(
            state.position,
            state.goal,
            state.width,
            state.height,
            state.terrain,
        )
        if target is None:
            return Move.UP

        dx, dy = target[0] - state.position[0], target[1] - state.position[1]
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
        return Move.UP
