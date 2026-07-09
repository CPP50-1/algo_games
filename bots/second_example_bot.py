"""Reference bot -- shows the minimum needed to implement the Bot API.

Strategy: keep going in the current direction; if that would kill you,
try the other three directions in a fixed priority order. No lookahead,
no space evaluation. This is a baseline to check the engine works and to
copy the API shape from, not a target -- trainees should beat it easily
once they reason more than one move ahead.
"""
from engine.bot import Bot, Move


class SecondExampleBot(Bot):
    def decide(self, state) -> Move:
        me = state.positions[state.self_id]

        def is_safe(move: Move) -> bool:
            x, y = me[0] + move.dx, me[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return (x, y) not in state.walls

        for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
            if is_safe(move):
                return move
        return Move.UP  # nothing is safe -- die predictably rather than crash
