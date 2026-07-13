"""
max_bot: picks the move that maximises reachable open space via flood fill.
1. Avoid obstacles — checks bounds, walls, and opponent proximity (Manhattan ≤ 1).
2. Evaluate space — BFS flood fill from each safe candidate cell.
3. Pick best — direction with the largest reachable area wins.
"""
from engine.bot import Bot, Move
from collections import deque


class MaxBot(Bot):
    def decide(self, state) -> Move:
        me = state.positions[state.self_id]

        other_positions = [
            pos for bid, pos in state.positions.items() if bid != state.self_id
        ]

        walls = set(state.walls)
        walls.update(state.positions.values())

        best_move = Move.RIGHT
        best_space = -1

        def _is_safe(x, y) -> bool:
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            if (x, y) in state.walls:
                return False
            for ox, oy in other_positions:
                if abs(x - ox) + abs(y - oy) <= 1:
                    return False
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
