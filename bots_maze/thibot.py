from typing import Any
import heapq

from engine.bot import Bot, Move

class Thibot(Bot):
    def decide(self, state: Any) -> Move:
        target = state.goal
        my_position = state.position

        if my_position == target:
            return None

        moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]

        def dijkstra():
            heap = [(0, my_position)]
            dist = {my_position: 0}
            prev = {my_position: None}   # pour reconstruire le chemin

            while heap:
                cost, (r, c) = heapq.heappop(heap)

                if (r, c) == target:
                    break


                if cost > dist.get((r, c), float('inf')):
                    continue

                for move in moves:
                    nr, nc = r + move.dx, c + move.dy
                    if not (0 <= nr < state.width and 0 <= nc < state.height):
                        continue

                    new_cost = cost + state.terrain[nc][nr]

                    if new_cost < dist.get((nr, nc), float('inf')):
                        dist[(nr, nc)] = new_cost
                        prev[(nr, nc)] = (r, c)
                        heapq.heappush(heap, (new_cost, (nr, nc)))

            return reconstruct_path(prev, target), dist.get(target, float('inf'))


        def reconstruct_path(prev, target):
            pathh = []
            node = target
            while node is not None:
                pathh.append(node)
                node = prev.get(node)
            return list(reversed(pathh))

        path, _ = dijkstra()

        x0, y0 = path[0]  # position actuelle
        x1, y1 = path[1]  # case suivante

        dx, dy = x1 - x0, y1 - y0

        if dy == -1: return Move.UP
        if dy == 1: return Move.DOWN
        if dx == -1: return Move.LEFT
        if dx == 1: return Move.RIGHT