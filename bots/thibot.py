from engine.bot import Bot, Move

class Thibot(Bot):
    def decide(self, state: Any) -> Move:
        my_position = state.positions[state.self_id]
        
        opponent_index = 1 if state.self_id == 0 else 0
        opponent_position = state.positions[opponent_index]
        
        if my_position[1] > opponent_position[1]:
            return Move.UP
        elif my_position[1] < opponent_position[1]:
            return Move.DOWN
        
        return Move.LEFT if my_position[0] < opponent_position[0] else Move.RIGHT
