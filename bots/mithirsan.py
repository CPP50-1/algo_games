import time
from collections import deque

from engine.bot import Bot, Move
from games.tron import Position, TronView

MOVES: set[Move] = {Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT}


def _neighbors(position: Position, occupied: set[Position], width: int, height: int):
    x, y = position
    for m in MOVES:
        nx, ny = x + m.dx, y + m.dy
        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in occupied:
            yield m, (nx, ny)


def _voronoi_score(
    my_position: Position,
    opponent_position: Position,
    occupied: set[Position],
    width: int,
    height: int,
):
    dist_me = {my_position: 0}
    dist_other = {opponent_position: 0}
    q_me, q_other = deque([my_position]), deque([opponent_position])

    while q_me:
        pos = q_me.popleft()
        for _, n in _neighbors(pos, occupied, width, height):
            if n not in dist_me:
                dist_me[n] = dist_me[pos] + 1
                q_me.append(n)
    while q_other:
        pos = q_other.popleft()
        for _, n in _neighbors(pos, occupied, width, height):
            if n not in dist_other:
                dist_other[n] = dist_other[pos] + 1
                q_other.append(n)

    score = 0
    all_cells = set(dist_me) | set(dist_other)
    for cell in all_cells:
        d_me = dist_me.get(cell, float("inf"))
        d_other = dist_other.get(cell, float("inf"))
        if d_me < d_other:
            score += 1
        elif d_other < d_me:
            score -= 1
    return score


def _minimax(
    my_position: Position,
    opponent_position: Position,
    occupied: set[Position],
    depth: int,
    maximizing: bool,
    alpha: float,
    beta: float,
    start_time: float,
    time_budget: float,
    width: int,
    height: int,
):
    if time.time() - start_time > time_budget or depth == 0:
        return _voronoi_score(my_position, opponent_position, occupied, width, height)

    if maximizing:
        my_moves = list(_neighbors(my_position, occupied, width, height))
        if not my_moves:
            return -1000
        best = float("-inf")
        for _, new_loc in my_moves:
            occupied.add(new_loc)
            val = _minimax(
                new_loc,
                opponent_position,
                occupied,
                depth - 1,
                False,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
            )
            occupied.remove(new_loc)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        other_moves = list(_neighbors(opponent_position, occupied, width, height))
        if not other_moves:
            return 1000
        best = float("inf")
        for _, new_loc in other_moves:
            occupied.add(new_loc)
            val = _minimax(
                my_position,
                new_loc,
                occupied,
                depth - 1,
                True,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
            )
            occupied.remove(new_loc)
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


class MithirsanTronBot(Bot):
    def decide(self, state: TronView) -> Move:

        opponent_id = next(
            bot_id
            for bot_id in state.positions
            if bot_id != state.self_id and bot_id in state.alive
        )

        TIME_BUDGET = 0.6
        start_time = time.time()

        me: Position = state.positions[state.self_id]
        opponent: Position = state.positions[opponent_id]
        occupied: set[Position] = set(state.walls) | {me, opponent}

        safe_moves = list(_neighbors(me, occupied, state.width, state.height))
        if not safe_moves:
            return Move.UP

        opponent_reachable = {
            loc for _, loc in _neighbors(opponent, occupied, state.width, state.height)
        }
        non_risky = [(m, loc) for m, loc in safe_moves if loc not in opponent_reachable]
        candidate_moves = non_risky if non_risky else safe_moves

        best_move = candidate_moves[0][0]

        for max_depth in range(2, 9, 2):
            if time.time() - start_time > TIME_BUDGET:
                break
            depth_best_move, depth_best_score = None, float("-inf")
            for move, new_loc in candidate_moves:
                if time.time() - start_time > TIME_BUDGET:
                    depth_best_move = None
                    break
                occupied.add(new_loc)
                score = _minimax(
                    new_loc,
                    opponent,
                    occupied,
                    max_depth - 1,
                    False,
                    float("-inf"),
                    float("inf"),
                    start_time,
                    TIME_BUDGET,
                    state.width,
                    state.height,
                )
                occupied.remove(new_loc)
                tie_breaker = (hash((state.self_id, move)) % 1000) * 1e-10
                adjusted = score + tie_breaker
                if adjusted > depth_best_score:
                    depth_best_move, depth_best_score = move, adjusted
            if depth_best_move is not None:
                best_move = depth_best_move

        x, y = me[0] + best_move.dx, me[1] + best_move.dy
        if (
            not (0 <= x < state.width and 0 <= y < state.height)
            or (x, y) in state.walls
        ):
            for m, _ in safe_moves:
                return m
            return Move.UP

        return best_move
