import select

from engine.bot import Bot, Move
import random

class SergioBot(Bot):
    #def decide(self, state):
        #Check the distance between bots / 2
            # can I go in that direction?
                #yes : move that way
                #no  : select another direction
        #return Move.UP


    def decide_random (self, state):
        my_position = state.positions[state.self_id]

        def is_safe(move: Move) -> bool:
            x, y = my_position[0] + move.dx, my_position[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return (x, y) not in state.walls

        moves = [Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT]
        for i in range(len(moves)):
            move = random.choice(moves)
            if is_safe(move):
                return move
            moves.remove(move)
        return Move.UP  # nothing is safe -- die predictably rather than crash

    ## Decide reasoning broken
    def decide_broken (self, state):
        my_position = state.positions[state.self_id]

        def is_safe(move: Move) -> bool:
            x, y = my_position[0] + move.dx, my_position[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return (x, y) not in state.walls

        def is_safer(move: Move) -> bool:
            a,b = my_position[0] + move.dx, my_position[1] + move.dy

            match move:
                case Move.UP:
                    b -= 1
                case Move.RIGHT:
                    a += 1
                case Move.DOWN:
                    b += 1
                case Move.LEFT:
                    a -= 1

            if not (0 <= a < state.width and 0 <= b < state.height):
                return False
            return (a,b) not in state.walls

        def is_appropriate(move: Move) -> bool:
            return furthermore(move) > 1

        def furthermore(move: Move) -> int:
            new_moves = [Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT]
            new_moves.remove(get_antagonist(move))  #Because i cannot come back
            result = 0
            for move in new_moves:
                if is_safer(move):
                    result += 1
            return result

        def get_antagonist(move: Move) -> Move:
            move_dict = {Move.UP:Move.DOWN, Move.RIGHT:Move.LEFT, Move.DOWN:Move.UP, Move.LEFT:Move.RIGHT}
            return move_dict[move]


        moves = [Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT]
        for i in range(len(moves)-1):
            move = random.choice(moves)
            if is_safe(move):
                if is_appropriate(move):
                    return move
            moves.remove(move)

        return moves[0]  # nothing is safe -- die predictably rather than crash


    def decide(self, state) -> Move:
        selected_move = Move.UP

        return selected_move