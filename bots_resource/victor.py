"""
Will calculate the best resources to get to with current score. Will ignore those where an enemy is closer.

"""
from engine.bot import Bot, Move
from games.resource import Item


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if dx > 0:
        return Move.RIGHT
    if dx < 0:
        return Move.LEFT
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    return Move.UP


class VictorResourceBot(Bot):
    def decide(self, state) -> Move:
        if not state.items:
            return Move.UP  # nothing left to do -- direction is irrelevant


        best_ratio = 0.0
        best_item = None
        enemies = []
        for enemy in state.positions.keys():
            if enemy != state.self_id:
                enemies.append(enemy)

        for item in state.items:
            distance_to_reach = abs(item.position[0] - state.position[0]) + abs(item.position[1] - state.position[1])
            closest_distance_enemy = 999
            for enemy in enemies:
                distance_enemy = abs(item.position[0] - state.positions[enemy][0]) + abs(item.position[1] - state.positions[enemy][1])
                if distance_enemy < closest_distance_enemy:
                    closest_distance_enemy = distance_enemy
            if distance_to_reach <= closest_distance_enemy:
                if state.moves_left > distance_to_reach:
                    time_value_ratio = item.value / distance_to_reach
                    if time_value_ratio > best_ratio:
                        best_ratio = time_value_ratio
                        best_item = item

        if best_item:
            return _step_toward(state.position, best_item.position)
        else:
            return _step_toward(state.position, (state.height / 2, state.width / 2))
