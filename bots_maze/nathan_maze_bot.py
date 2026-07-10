import heapq
from engine.bot import Bot, Move


def _dijkstra_next_step(position, goal, width, height, terrain):
    if position == goal:
        return None

    best = {position: 0}
    p = [(0, position, None)]

    while p:
        dist, pos, step = heapq.heappop(p)
        if dist > best.get(pos, float("inf")):
            continue
        if pos == goal:
            return step

    return None


class MazeBot(Bot):
    def decide(self, state) -> Move:
        target = _dijkstra_next_step(state.position, state.goal, state.width, state.height, state.terrain)
        if target is None:
            return Move.UP
        dx, dy = target[0] - state.position[0], target[1] - state.position[1]
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
        return Move.UP