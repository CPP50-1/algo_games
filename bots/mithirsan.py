import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from engine.bot import Bot, Move
from games.tron import Position, TronView

MOVES: Tuple[Move, ...] = (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT)
MOVE_ORDER = {Move.UP: 0, Move.RIGHT: 1, Move.DOWN: 2, Move.LEFT: 3}
RIGHT_TURNS = {
    Move.UP: Move.RIGHT,
    Move.RIGHT: Move.DOWN,
    Move.DOWN: Move.LEFT,
    Move.LEFT: Move.UP,
}
LEFT_TURNS = {
    Move.UP: Move.LEFT,
    Move.LEFT: Move.DOWN,
    Move.DOWN: Move.RIGHT,
    Move.RIGHT: Move.UP,
}


def _neighbors(
    position: Position,
    occupied: Set[Position],
    width: int,
    height: int,
) -> List[Tuple[Move, Position]]:
    x, y = position
    result = []
    for m in MOVES:
        nx, ny = x + m.dx, y + m.dy
        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in occupied:
            result.append((m, (nx, ny)))
    return result


def _flood_fill(
    start: Position,
    occupied: Set[Position],
    width: int,
    height: int,
    max_cells: int = 8000,
) -> Dict[Position, int]:
    """BFS flood fill returning distance map from start."""
    dist = {start: 0}
    q = deque([start])
    while q and len(dist) < max_cells:
        pos = q.popleft()
        d = dist[pos]
        x, y = pos
        for m in MOVES:
            nx, ny = x + m.dx, y + m.dy
            if 0 <= nx < width and 0 <= ny < height:
                npos = (nx, ny)
                if npos not in occupied and npos not in dist:
                    dist[npos] = d + 1
                    q.append(npos)
    return dist


def _evaluate_position(
    my_pos: Position,
    opponent_positions: List[Position],
    occupied: Set[Position],
    width: int,
    height: int,
    my_dist: Optional[Dict[Position, int]] = None,
    opp_dists: Optional[List[Dict[Position, int]]] = None,
) -> float:
    """
    Evaluate position using territory control + mobility.
    Territory: cells I reach before all opponents.
    Mobility: my reachable cells (survival potential).
    """
    if my_dist is None:
        my_dist = _flood_fill(my_pos, occupied, width, height)

    if not my_dist:
        return -10000.0

    if opp_dists is None:
        opp_dists = [
            _flood_fill(op, occupied, width, height) for op in opponent_positions
        ]

    territory = 0
    contested = 0
    for cell, d in my_dist.items():
        best_opp = min(
            (od.get(cell, float("inf")) for od in opp_dists), default=float("inf")
        )
        if d < best_opp:
            territory += 1
        elif d == best_opp:
            contested += 1

    mobility = len(my_dist)
    survival_bonus = 100 if mobility > 15 else (50 if mobility > 8 else 0)

    territory_weight = 1.5 if len(opponent_positions) > 1 else 2.0
    contested_penalty = 0.5 * contested

    score = (
        territory_weight * territory
        - contested_penalty
        + 0.3 * mobility
        + survival_bonus
    )
    return score


def _minimax_multi(
    my_pos: Position,
    opponent_positions: List[Position],
    occupied: Set[Position],
    depth: int,
    my_turn: bool,
    alpha: float,
    beta: float,
    start_time: float,
    time_budget: float,
    width: int,
    height: int,
    opponent_index: int = 0,
) -> float:
    """
    Minimax with multiple opponents.
    Models all opponents as a single minimizing player.
    """
    if time.time() - start_time > time_budget or depth == 0:
        return _evaluate_position(my_pos, opponent_positions, occupied, width, height)

    if my_turn:
        my_moves = _neighbors(my_pos, occupied, width, height)
        if not my_moves:
            return -10000.0

        best = float("-inf")
        for _, new_pos in my_moves:
            occupied.add(new_pos)
            val = _minimax_multi(
                new_pos,
                opponent_positions,
                occupied,
                depth - 1,
                False,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
                0,
            )
            occupied.remove(new_pos)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        if opponent_index >= len(opponent_positions):
            return _minimax_multi(
                my_pos,
                opponent_positions,
                occupied,
                depth,
                True,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
                0,
            )

        opp_pos = opponent_positions[opponent_index]
        opp_moves = _neighbors(opp_pos, occupied, width, height)

        if not opp_moves:
            return _minimax_multi(
                my_pos,
                opponent_positions,
                occupied,
                depth,
                False,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
                opponent_index + 1,
            )

        best = float("inf")
        for _, new_pos in opp_moves:
            occupied.add(new_pos)
            val = _minimax_multi(
                my_pos,
                opponent_positions,
                occupied,
                depth,
                False,
                alpha,
                beta,
                start_time,
                time_budget,
                width,
                height,
                opponent_index + 1,
            )
            occupied.remove(new_pos)
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def _wall_follow_score(
    move: Move, pos: Position, occupied: Set[Position], width: int, height: int
) -> float:
    """Prefer moves that keep a wall on the right (wall-following survival strategy)."""
    x, y = pos
    right = RIGHT_TURNS[move]
    left = LEFT_TURNS[move]

    rx, ry = x + right.dx, y + right.dy
    lx, ly = x + left.dx, y + left.dy

    right_blocked = not (0 <= rx < width and 0 <= ry < height) or (rx, ry) in occupied
    left_blocked = not (0 <= lx < width and 0 <= ly < height) or (lx, ly) in occupied

    if right_blocked and not left_blocked:
        return 1.0
    if not right_blocked and left_blocked:
        return -1.0
    return 0.0


def _move_quality_score(
    move: Move,
    new_pos: Position,
    my_pos: Position,
    opponent_positions: List[Position],
    occupied: Set[Position],
    width: int,
    height: int,
    my_dist: Dict[Position, int],
    opp_dists: List[Dict[Position, int]],
    turn: int,
) -> float:
    """
    Tiebreaker score combining:
    1. Territory evaluation (main heuristic)
    2. Wall-following tendency (survival strategy)
    3. Move ordering consistency (deterministic)
    4. Avoid moving toward nearest opponent
    """
    territory_score = _evaluate_position(
        new_pos, opponent_positions, occupied, width, height, my_dist, opp_dists
    )

    wall_score = _wall_follow_score(move, new_pos, occupied, width, height) * 0.1

    move_order_score = (3 - MOVE_ORDER.get(move, 0)) * 1e-4

    nearest_opp_dist = (
        min(
            abs(new_pos[0] - op[0]) + abs(new_pos[1] - op[1])
            for op in opponent_positions
        )
        if opponent_positions
        else 100
    )
    distance_penalty = -0.01 * max(0, 5 - nearest_opp_dist)

    rng_seed = hash((my_pos[0], my_pos[1], turn, move)) % 10000
    randomness = (rng_seed / 10000.0) * 1e-6

    return (
        territory_score + wall_score + move_order_score + distance_penalty + randomness
    )


class MithirsanTronBot(Bot):
    def decide(self, state: TronView) -> Move:
        start_time = time.time()

        me = state.positions[state.self_id]
        alive_opponents = [
            state.positions[bid] for bid in state.alive if bid != state.self_id
        ]

        if not alive_opponents:
            return Move.UP

        occupied: Set[Position] = set(state.walls) | {me} | set(alive_opponents)

        safe_moves = _neighbors(me, occupied, state.width, state.height)
        if not safe_moves:
            return Move.UP

        opponent_reachable = set()
        for op in alive_opponents:
            for _, loc in _neighbors(op, occupied, state.width, state.height):
                opponent_reachable.add(loc)

        non_risky = [(m, loc) for m, loc in safe_moves if loc not in opponent_reachable]
        candidate_moves = non_risky if non_risky else safe_moves

        num_opponents = len(alive_opponents)
        turn = state.turn

        # Adaptive time budget: default tournament timeout is 1.0s, leave margin for subprocess overhead
        base_budget = 0.45 if num_opponents >= 3 else 0.50
        turn_factor = min(turn / 100.0, 0.1)
        time_budget = base_budget - turn_factor

        # Pre-compute distance maps for this turn
        my_dist = _flood_fill(me, occupied, state.width, state.height)
        opp_dists = [
            _flood_fill(op, occupied, state.width, state.height)
            for op in alive_opponents
        ]

        best_move = candidate_moves[0][0]

        # Adaptive depth: shallower for more opponents, deeper for 1v1
        max_depth = 2 if num_opponents >= 3 else (3 if num_opponents == 2 else 4)

        for depth in range(1, max_depth + 1):
            if time.time() - start_time > time_budget:
                break

            depth_best_move = None
            depth_best_score = float("-inf")

            for move, new_loc in candidate_moves:
                if time.time() - start_time > time_budget:
                    depth_best_move = None
                    break

                occupied.add(new_loc)

                minimax_score = _minimax_multi(
                    new_loc,
                    alive_opponents,
                    occupied,
                    depth - 1,
                    False,
                    float("-inf"),
                    float("inf"),
                    start_time,
                    time_budget,
                    state.width,
                    state.height,
                )

                occupied.remove(new_loc)

                quality = _move_quality_score(
                    move,
                    new_loc,
                    me,
                    alive_opponents,
                    occupied,
                    state.width,
                    state.height,
                    my_dist,
                    opp_dists,
                    turn,
                )

                combined = minimax_score * 0.7 + quality * 0.3

                if combined > depth_best_score:
                    depth_best_score = combined
                    depth_best_move = move

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
