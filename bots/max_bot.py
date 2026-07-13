from engine.bot import Bot, Move
from collections import deque


class MaxBot(Bot):
    def decide(self, state) -> Move:
        me = state.positions[state.self_id]

        walls = set(state.walls)
        walls.update(state.positions.values())

        best_move = Move.RIGHT
        best_space = -1

        def _is_safe(x, y) -> bool:
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            if (x, y) in state.walls:
                return False
            # adjacent_tiles = self._adjacent(self, x, y)
            # for tile in adjacent_tiles:
            #     if tile in other_positions:
            #         return False

            return True

        for move in Move:
            nx, ny = me[0] + move.dx, me[1] + move.dy

            if not _is_safe(nx, ny):
                continue

            space = self._flood_fill(nx, ny, walls, state.width, state.height)
            if space > best_space:
                best_space = space
                best_move = move

        return best_move

    def _flood_fill(self, x: int, y: int, walls: set, w: int, h: int) -> int:
        seen = set()
        q = deque()
        q.append((x, y))
        seen.add((x, y))
        while q:
            cx, cy = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                if (nx, ny) in walls or (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                q.append((nx, ny))
        return len(seen)

    def _adjacent(self, x, y) -> list[tuple[int, int]]:
        return [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
