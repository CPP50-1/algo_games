from engine.bot import Bot, Move


"""
self_id     -- your bot id
width       -- board width
height      -- board height
turn        -- current turn number
positions   -- {bot_id: (x, y)} for every bot still alive
alive       -- list of bot ids still alive
walls       -- frozenset of every occupied (x, y) cell, anyone's trail

Up = +y
Right = +x
Down = -y
Left = -x
"""
class VictorBot(Bot):

    _grid : dict[tuple[int, int], int] | None = None
    enemies_last_pos : dict[int, tuple[int, int]] | None = None
    enemy_direction :dict[int, str] | None = None
    order : str = 'prepare'

    @classmethod
    def create_grid(cls, state):
        cls._grid = {}
        for x in range(state.width):
            for y in range(state.height):
                cls._grid[(x, y)] = 0
        for cell in state.positions:
            cls._grid[cell] = 1
        for cell in state.walls:
            cls._grid[cell] = 1

    @classmethod
    def update_grid(cls, state):
        for cell in state.positions:
            cls._grid[cell] = 1

    @classmethod
    def get_grid(cls, state):
        if cls._grid is None:
            cls.create_grid(state)
        return cls._grid


    def decide(self, state) -> Move:
        my_pos = state.positions[state.self_id]
        grid = self.get_grid(state)
        current_positions = state.positions
        enemies = []
        enemy = None

        def get_distance(entity):
            enemy_pos = current_positions[entity]
            distance = abs(enemy_pos[0] - my_pos[0]) + abs(enemy_pos[0] - my_pos[0])
            return distance

        def is_safe(move: Move) -> bool:
            x, y = my_pos[0] + move.dx, my_pos[1] + move.dy
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return not bool(grid[(x, y)])

        def is_dangerous(move: Move) -> bool:
            x, y = my_pos[0] + move.dx, my_pos[1] + move.dy
            if move.dy:
                if grid[(x + 1, y)] and grid[(x - 1, y)]:
                    return False
            else:
                if grid[(x, y + 1)] and grid[(x, y - 1)]:
                    return False
            return True

        def safe_move() -> Move:
            if get_distance(enemy) <=4:
                if current_positions[enemy][1] == my_pos[1]:
                    return Move.UP if is_safe(Move.UP) else Move.DOWN
                if current_positions[enemy][0] == my_pos[0]:
                    return Move.LEFT if is_safe(Move.LEFT) else Move.RIGHT
            safe_moves = []
            for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
                if is_safe(move):
                    safe_moves.append(move)
            for move in safe_moves:
                if not is_dangerous(move):
                    return move
            return safe_moves[0]

        def _step_toward(position, target):
            dx = target[0] - position[0]
            dy = target[1] - position[1]
            if dx > 0 and is_safe(Move.RIGHT):
                return Move.RIGHT
            if dx < 0 and is_safe(Move.LEFT):
                return Move.LEFT
            if dy > 0 and is_safe(Move.DOWN):
                return Move.DOWN
            if dy < 0 and is_safe(Move.UP):
                return Move.UP
            return safe_move()

        for id_ in current_positions.keys():
            if id_ != state.self_id:
                enemies.append(id_)

        enemy = enemies[0]

        # if VictorBot.enemies_last_pos:
        #     for enemy in enemies:
        #         current = current_positions[enemy]
        #         last = VictorBot.enemies_last_pos[enemy]
        #         if current[0] == last[0]:
        #             # vertical
        #             if current[1] > last[1]:
        #                 # down
        #                 direction = 'down'
        #             else:
        #                 # up
        #                 direction = 'up'
        #         else:
        #             # horizontal
        #             if current[0] > last[0]:
        #                 # right
        #                 direction = 'right'
        #             else:
        #                 #left
        #                 direction = 'left'
        #         VictorBot.enemy_direction[enemy] = direction

        if state.turn != 0:
             self.update_grid(state)

        VictorBot.enemies_last_pos = current_positions

        if state.turn == 0 or state.turn == 1:

            if state.turn == 0:
                if current_positions[enemy][0] < my_pos[0]:
                    return Move.LEFT if is_safe(Move.LEFT) else safe_move()
                else:
                    return Move.RIGHT if is_safe(Move.RIGHT) else safe_move()

        if get_distance(enemy) > 4:
            return _step_toward(my_pos ,current_positions[enemy])
        return safe_move()