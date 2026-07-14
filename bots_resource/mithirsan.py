from engine.bot import Bot, Move
from games.resource import Item, ResourceView, Position


def _step_toward(position: Position, target: Position):
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


def _step_count(position: Position, target: Position) -> int:
    return abs(position[0] - target[0]) + abs(position[1] - target[1])


def _opponent_distances(my_id, opponents, items):
    best = {}
    for item in items:
        closest = min(
            [
                _step_count(pos, item.position)
                for bot_id, pos in opponents.items()
                if bot_id != my_id
            ]
        )
        best[item] = closest
    return best


def _knapsack(capacity, values, steps):
    n = len(values)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        for w in range(1, capacity + 1):
            if steps[i - 1] <= w:
                dp[i][w] = max(
                    dp[i - 1][w],
                    dp[i - 1][w - steps[i - 1]] + values[i - 1],
                )
            else:
                dp[i][w] = dp[i - 1][w]

    selected = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(i - 1)
            w -= steps[i - 1]

    return dp[n][capacity], selected


class MithirsanResourceBot(Bot):
    def decide(self, state: ResourceView) -> Move:
        if not state.items:
            return Move.UP  # nothing left to do -- direction is irrelevant

        items_distance: dict[Item, int] = dict()

        opponent_item_distance = _opponent_distances(
            state.self_id,
            state.positions,
            state.items,
        )

        for item in state.items:
            my_distance: int = _step_count(state.position, item.position)

            if my_distance > opponent_item_distance.get(item, 5):
                continue

            items_distance[item] = my_distance

        _, selected_indices = _knapsack(
            state.moves_left,
            [it.value for it in items_distance],
            [items_distance[it] for it in items_distance],
        )

        if not selected_indices:
            return Move.UP

        items_list: list[Item] = list(items_distance.keys())
        target_item = min(
            (items_list[i] for i in selected_indices),
            key=lambda it: items_distance[it],
        )

        return _step_toward(state.position, target_item.position)
