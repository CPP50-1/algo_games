"""
max_bot (tron): Voronoi territory evaluation + negamax with alpha-beta
pruning, time-budgeted iterative deepening, and draw-seeking behaviour.

Why this beats plain flood fill:
  - Voronoi BFS from BOTH players simultaneously: each cell is owned
    by whoever reaches it first. The difference (our cells - their cells)
    is the score — much more accurate than raw space.
  - Negamax + alpha-beta: simulates opponent replies instead of assuming
    they stand still, so we don't walk into traps.
  - Time-budgeted iterative deepening: always has a usable result even
    if a deeper search gets cut off mid-way.
  - Collision avoidance: never moves to a cell orthogonally adjacent
    to the opponent (Manhattan ≤ 1), and never lands on a cell the
    opponent could also reach this turn (head-on crash).
  - Draw preference: when the current player has no moves but the
    opponent is also trapped, scores it as a draw (0) instead of a
    loss (‑1000).  Prefers a draw over a certain loss.
"""

import time
from collections import deque
from engine.bot import Bot, Move

MOVES = (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT)
TIME_BUDGET = 0.7


class _SearchTimeout(Exception):
    pass


class MaxBot(Bot):
    def decide(self, state) -> Move:
        deadline = time.monotonic() + TIME_BUDGET
        me = state.positions[state.self_id]
        other = next(
            pos for pid, pos in state.positions.items() if pid != state.self_id
        )
        occupied = set(state.walls) | {me, other}

        def neighbors(pos, occ):
            x, y = pos
            for m in MOVES:
                nx, ny = x + m.dx, y + m.dy
                if (
                    0 <= nx < state.width
                    and 0 <= ny < state.height
                    and (nx, ny) not in occ
                ):
                    yield m, (nx, ny)

        def voronoi(my_pos, opp_pos, occ):
            d1, d2 = {my_pos: 0}, {opp_pos: 0}
            q1, q2 = deque([my_pos]), deque([opp_pos])
            while q1 or q2:
                for q, d in ((q1, d1), (q2, d2)):
                    if q:
                        cur = q.popleft()
                        for _, n in neighbors(cur, occ):
                            if n not in d:
                                d[n] = d[cur] + 1
                                q.append(n)
            score = 0
            for cell in set(d1) | set(d2):
                a, b = d1.get(cell, 99999), d2.get(cell, 99999)
                if a < b:
                    score += 1
                elif b < a:
                    score -= 1
            return score

        def negamax(my_pos, opp_pos, occ, depth, alpha, beta):
            if time.monotonic() > deadline:
                raise _SearchTimeout()
            if depth == 0:
                return voronoi(my_pos, opp_pos, occ)
            moves = list(neighbors(my_pos, occ))
            moves = [
                (m, loc)
                for m, loc in moves
                if abs(loc[0] - opp_pos[0]) + abs(loc[1] - opp_pos[1]) > 1
            ]
            if not moves:
                if not list(neighbors(opp_pos, occ)):
                    return 0
                return -1000
            best = -99999
            for _, next_pos in moves:
                occ.add(next_pos)
                val = -negamax(opp_pos, next_pos, occ, depth - 1, -beta, -alpha)
                occ.remove(next_pos)
                if val > best:
                    best = val
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    break
            return best

        safe = list(neighbors(me, occupied))
        safe = [
            (m, loc)
            for m, loc in safe
            if abs(loc[0] - other[0]) + abs(loc[1] - other[1]) > 1
        ]
        if not safe:
            return Move.UP

        # Head-on collision filter: never gamble on shared cells
        opp_reach = {loc for _, loc in neighbors(other, occupied)}
        candidates = [(m, loc) for m, loc in safe if loc not in opp_reach]
        if not candidates:
            candidates = safe

        best_move = candidates[0][0]
        try:
            for depth in range(2, min(14, state.width * state.height), 2):
                current_best = None
                current_val = -99999
                for move, next_pos in candidates:
                    if time.monotonic() > deadline:
                        raise _SearchTimeout()
                    occupied.add(next_pos)
                    val = -negamax(other, next_pos, occupied, depth - 1, -99999, 99999)
                    occupied.remove(next_pos)
                    if val > current_val:
                        current_val = val
                        current_best = move
                if current_best is not None:
                    best_move = current_best
        except _SearchTimeout:
            pass  # keep best_move from the last completed depth

        # Safety net: ensure the final move is in-bounds and not on a trail
        nx, ny = me[0] + best_move.dx, me[1] + best_move.dy
        if (
            not (0 <= nx < state.width and 0 <= ny < state.height)
            or (nx, ny) in state.walls
        ):
            # Fall back: pick the first genuinely safe candidate
            for m, loc in safe:
                if (
                    0 <= loc[0] < state.width
                    and 0 <= loc[1] < state.height
                    and loc not in state.walls
                ):
                    return m
            return Move.UP
        return best_move
