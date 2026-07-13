from typing import Any
from collections import deque

from engine.bot import Bot, Move



class Thibot(Bot):
    def decide(self, state: Any) -> Move:
        my_position = state.positions[state.self_id]
        moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]
        next_turn_enemies = []
        enemies_position = [position for position in state.positions.values() if position != my_position]


        for ennemi_position in enemies_position:
            for move in moves:
                next_turn_enemies.append((ennemi_position[0] +  move.dx, ennemi_position[1] + move.dy))

        def is_safe(x, y) -> bool:
            if (not (0 <= x < state.width  and 0 <= y < state.height )
                    or (x, y) in state.positions
                    or (x, y) in next_turn_enemies
                    or (x, y) in state.walls):
                return False
            return True


        def count_reachable(x,y):
            queue = deque([(x,y)])
            visited = {(x,y)}

            while queue:
                r, c = queue.popleft()
                for move in moves:
                    nr,nc = r+move.dx, c+move.dy
                    if is_safe(nr,nc) and (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
            return len(visited)

        def best_move()->Move:
            best = -1
            best_dir = None
            for move in moves:
                nr, nc = my_position[0]+ move.dx, my_position[1] + move.dy
                if is_safe(nr,nc):
                    space = count_reachable(nr, nc)
                    if space > best:
                        best = space
                        best_dir = move
            return best_dir

        return best_move()


