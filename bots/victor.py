from engine.bot import Bot, Move



class VictorBot(Bot):
    """
    Will go towards the enemy and avoid clashing cells and single cell paths as much as possible
    """
    def decide(self, state) -> Move:
        my_pos = state.positions[state.self_id]
        current_positions = state.positions
        enemies = []

        def is_safe(move: Move) -> bool:
            x, y = my_pos[0] + move.dx, my_pos[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False                                        # if it's outside of bounds : not safe
            for selected_enemy in enemies:
                enemy_pos = state.positions[selected_enemy]
                if abs(x - enemy_pos[0])+abs(y - enemy_pos[1])==1:
                    return False                                    # if it's a cell an enemy can reach : not safe
            return (x, y) not in state.walls                        # if it's a wall : not safe

        def is_safe_path(move: Move) -> bool:
            x, y = my_pos[0] + move.dx, my_pos[1] + move.dy
            # if the path taken is only 1 cell wide, it's not safe
            if move.dy:
                if ((x + 1, y) in state.walls or x+1 >= state.width) and ((x - 1, y) in state.walls or x-1 < 0):
                    return False
            else:
                if ((x, y+1) in state.walls or y+1 >= state.height) and ((x, y-1) in state.walls or y-1 < 0):
                    return False
            return True

        def safe_move() -> Move:
            # will be used when no path towards the enemy is safe.
            # we check every move possible, and how safe it is, then return the move
            safe_moves = []
            for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
                if is_safe(move):
                    safe_moves.append(move)
            for move in safe_moves:
                if is_safe_path(move):
                    return move
            return safe_moves[0] if safe_moves else Move.UP

        def _step_toward(position, target):
            dx = target[0] - position[0]
            dy = target[1] - position[1]
            if dx > 0 and is_safe(Move.RIGHT) and is_safe_path(Move.RIGHT):
                return Move.RIGHT
            if dx < 0 and is_safe(Move.LEFT) and is_safe_path(Move.LEFT):
                return Move.LEFT
            if dy > 0 and is_safe(Move.DOWN) and is_safe_path(Move.DOWN):
                return Move.DOWN
            if dy < 0 and is_safe(Move.UP) and is_safe_path(Move.UP):
                return Move.UP
            return safe_move()

        for id_ in current_positions.keys():
            if id_ != state.self_id:
                enemies.append(id_)

        enemy = enemies[0]

        return _step_toward(my_pos ,current_positions[enemy])