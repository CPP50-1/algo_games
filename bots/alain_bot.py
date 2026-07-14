from engine.bot import Bot, Move
from games.tron import TronView

aggressive_mode = True
lookahead_depth = 5

class AlainBot(Bot):

    def decide(self, state:TronView) -> Move:
        '''
        decide(state) gets a TronView:
        self_id     - your bot id
        width       - board width
        height      - board height
        turn        - current turn number
        positions   - {bot_id: (x, y)} for every bot still alive
        alive       - list of bot ids still alive
        walls        frozenset of every occupied (x, y) cell, anyone's trail

        '''

        def is_safe(move: Move) -> bool:
            x, y = me[0] + move.dx, me[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return ((x, y) not in state.walls) and ((x, y) not in state.positions)

        def distance(me:tuple, other:tuple) ->int:
            return abs(me[0] - other[0]) + abs(me[1] - other[1])

        def eval_neighbouring(position:tuple, my_trace:set, depth=1) -> float:
            if depth == 0:
                return 0
            else:
                up = position[0], max(0,position[1]-1)
                down = position[0], min(state.height-1, position[1]+1)
                right = min(position[0]+1, state.width-1), position[1]
                left = max(0, position[0]-1), position[1]
                value = (  (0 if (up in my_trace or up in state.walls or up in bot_positions) else (1 + eval_neighbouring(up, my_trace | {up}, depth-1)))
                         + (0 if (down in my_trace or down in state.walls or down in bot_positions) else (1 + eval_neighbouring(down, my_trace | {down}, depth-1)))
                         + (0 if (right in my_trace or right in state.walls or right in bot_positions) else (1 + eval_neighbouring(right, my_trace | {right}, depth-1)))
                         + (0 if (left in my_trace or left in state.walls or left in bot_positions) else (1 + eval_neighbouring(left, my_trace | {left}, depth-1)))
                         )
                return value / (depth * 2)

        me = state.positions[state.self_id]
        my_trace = {me}
        bot_positions = set(state.positions.values())


        center = state.height // 2, state.width // 2

        _, closest_bot_position = min([(distance(me, bot_pos), bot_pos) for bot_id,bot_pos in state.positions.items() if bot_id!=state.self_id])

        evals = [(eval_neighbouring((me[0] + move.dx, me[1] + move.dy), my_trace, lookahead_depth), move)
                    for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT) if is_safe(move)]

        # Additionally to the evaluation, consider the distance to the closest bot and to the center
        # In aggressive mode, we consider reducing the distance to the closest bot.
        move = max(evals, key=lambda eval_move:
                            (eval_move[0] / (distance((me[0] + eval_move[1].dx, me[1] + eval_move[1].dy),
                                                            closest_bot_position)
                                            + distance( me, center))) if aggressive_mode
                            else
                            (eval_move[0] * (distance((me[0] + eval_move[1].dx, me[1] + eval_move[1].dy),
                                                      closest_bot_position))
                                             / distance(me, center))

                   )
        return move[1]
