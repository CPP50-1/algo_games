"""Reference bot -- shows the minimum needed to implement the Bot API.

Strategy: keep going in the current direction; if that would kill you,
try the other three directions in a fixed priority order. No lookahead,
no space evaluation. This is a baseline to check the engine works and to
copy the API shape from, not a target -- trainees should beat it easily
once they reason more than one move ahead.
"""

from engine.bot import Bot, Move
from collections import deque


class JulienBot(Bot):
    def decide(self, state) -> Move:
        me = state.positions[state.self_id]
        curr_x, curr_y = me

        MAX_DEPTH = (state.height * state.width) - len(state.walls)

        def is_safe(x: int, y: int, move: Move) -> bool:
            next_x, next_y = x + move.dx, y + move.dy

            if not (0 <= next_x < state.width and 0 <= next_y < state.height):
                return False

            return (next_x, next_y) not in state.walls

        best_first_move = None
        best_length = -1

        moves = []

        center_x = state.width / 2
        center_y = state.height / 2

        # Vertical priority
        if curr_y < center_y:
            moves.append(Move.DOWN)
        else:
            moves.append(Move.UP)

        # Horizontal priority
        if curr_x < center_x:
            moves.append(Move.RIGHT)
        else:
            moves.append(Move.LEFT)

        # Add the remaining directions as fallbacks
        for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
            if move not in moves:
                moves.append(move)

        # Try every possible first move
        for first_move in moves:
            if not is_safe(curr_x, curr_y, first_move):
                continue

            start_x = curr_x + first_move.dx
            start_y = curr_y + first_move.dy

            queue = deque([(start_x, start_y, 1)])
            visited = {(start_x, start_y)}

            longest = 1

            while queue:
                x, y, depth = queue.popleft()
                longest = max(longest, depth)

                if depth >= MAX_DEPTH:
                    continue

                for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
                    if not is_safe(x, y, move):
                        continue

                    nx = x + move.dx
                    ny = y + move.dy

                    if (nx, ny) in visited:
                        continue

                    visited.add((nx, ny))
                    queue.append((nx, ny, depth + 1))

            if longest > best_length:
                best_length = longest
                best_first_move = first_move

        if best_first_move is not None:
            return best_first_move

        return Move.UP
