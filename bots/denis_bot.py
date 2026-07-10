"""Reference bot -- shows the minimum needed to implement the Bot API.

Strategy: keep going in the current direction; if that would kill you,
try the other three directions in a fixed priority order. No lookahead,
no space evaluation. This is a baseline to check the engine works and to
copy the API shape from, not a target -- trainees should beat it easily
once they reason more than one move ahead.
"""
from engine.bot import Bot, Move
from run_tournament import melist

class ExampleBot(Bot):
    def decide(self, state) -> Move:
        me = list(state.positions[state.self_id])

        def is_safe(me, move: Move, walls) -> bool:
            x, y = me[0] + move.dx, me[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return (x, y) not in walls

        def walk_tree(level):
            while level < 40:
                for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
                    if level == 0:
                        walls = state.walls.copy()
                        final_move = move
                    if is_safe(me, move, walls):
                        me[0], me[1] = me[0] + move.dx, me[1] + move.dy
                        print(me)
                        level += 1
                        walls.add(me)
                        walk_tree(level)
                        if level == 40:
                            return final_move
            return walk_tree()
        level = 0
        final_move = Move.UP
        walk_tree(level)# nothing is safe -- die predictably rather than crash

if __name__ == "__main__":
    from games.tron import TronView
    from typing import FrozenSet
    state = TronView(
        "1",
        21,
        21,
        turn=0,
        positions={"1": (2,10),"2": (18,10)},
        alive=("1", "2"),
        walls={(2,10),(18,10)},
    )

    ExampleBot().decide(state)
