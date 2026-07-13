import select

from engine.bot import Bot, Move
import random

class SergioBot(Bot):
    def __init__(self):
        super().__init__()
        self._safe_distance = 3
        self._original_moves = [Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT]
        self._opposite_moves = {Move.UP : Move.DOWN, Move.RIGHT : Move.LEFT, Move.DOWN : Move.UP, Move.LEFT : Move.RIGHT}

    #_random_v2
    def decide(self, state):
        me = state.positions[state.self_id]
        possible_moves = self._original_moves


        def is_safe(move: Move) -> bool:
            x, y = me[0] + move.dx, me[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            move_surrounds = [(x,y),(x+1, y), (x-1, y), (x, y+1), (x, y-1)]         # Check surrounds of the movement trying to avoid to get self trapped
            count = sum(t in move_surrounds for t in state.walls)                   # How many movements can I do if I took that direction

            return count <= 2                                                       # Do not move in that direction if one or zero movements can be donne afterward

        for _ in range(len(possible_moves)):
            move = random.choice(possible_moves)
            possible_moves.remove(move)
            if is_safe(move):
                return move
        return Move.UP  # nothing is safe -- die predictably rather than crash


