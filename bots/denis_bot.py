"""Tron bot -- minimax search with a Voronoi-style heuristic and
iterative deepening, bounded by a time budget.

Strategy: each turn, explore possible moves while also anticipating the
opponent's responses (minimax + alpha-beta pruning), and evaluate each
reached position with a Voronoi-style flood fill (who controls more
territory?). Iterative deepening guarantees we always have a usable
result even if there isn't enough time to search very deep.
"""
import time
from collections import deque

from engine.bot import Bot, Move

MOVES = (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT)


class DenisBot(Bot):
    def decide(self, state) -> Move:
        me_id = state.self_id
        other_id = next(pid for pid in state.positions if pid != me_id)

        TIME_BUDGET = 0.6
        start_time = time.time()

        def neighbors(loc, occupied):
            x, y = loc
            for m in MOVES:
                nx, ny = x + m.dx, y + m.dy
                if 0 <= nx < state.width and 0 <= ny < state.height and (nx, ny) not in occupied:
                    yield m, (nx, ny)

        def voronoi_score(my_loc, other_loc, occupied):
            """Simultaneous BFS: +1 for each cell I reach first, -1 for the opponent."""
            dist_me = {my_loc: 0}
            dist_other = {other_loc: 0}
            q_me, q_other = deque([my_loc]), deque([other_loc])

            while q_me:
                loc = q_me.popleft()
                for _, n in neighbors(loc, occupied):
                    if n not in dist_me:
                        dist_me[n] = dist_me[loc] + 1
                        q_me.append(n)
            while q_other:
                loc = q_other.popleft()
                for _, n in neighbors(loc, occupied):
                    if n not in dist_other:
                        dist_other[n] = dist_other[loc] + 1
                        q_other.append(n)

            score = 0
            all_cells = set(dist_me) | set(dist_other)
            for cell in all_cells:
                d_me = dist_me.get(cell, float('inf'))
                d_other = dist_other.get(cell, float('inf'))
                if d_me < d_other:
                    score += 1
                elif d_other < d_me:
                    score -= 1
                # tie: nobody "owns" the cell, skip it
            return score

        def minimax(my_loc, other_loc, occupied, depth, maximizing, alpha, beta):
            if time.time() - start_time > TIME_BUDGET or depth == 0:
                return voronoi_score(my_loc, other_loc, occupied)

            if maximizing:
                my_moves = list(neighbors(my_loc, occupied))
                if not my_moves:
                    return -1000  # I'm dead on this branch
                best = float('-inf')
                for _, new_loc in my_moves:
                    occupied.add(new_loc)
                    val = minimax(new_loc, other_loc, occupied, depth - 1, False, alpha, beta)
                    occupied.remove(new_loc)
                    best = max(best, val)
                    alpha = max(alpha, best)
                    if beta <= alpha:
                        break
                return best
            else:
                other_moves = list(neighbors(other_loc, occupied))
                if not other_moves:
                    return 1000  # the opponent is dead on this branch
                best = float('inf')
                for _, new_loc in other_moves:
                    occupied.add(new_loc)
                    val = minimax(my_loc, new_loc, occupied, depth - 1, True, alpha, beta)
                    occupied.remove(new_loc)
                    best = min(best, val)
                    beta = min(beta, best)
                    if beta <= alpha:
                        break
                return best

        me = tuple(state.positions[me_id])
        other = tuple(state.positions[other_id])
        occupied = set(state.walls) | {me, other}

        safe_moves = list(neighbors(me, occupied))
        if not safe_moves:
            return Move.UP

        # Cells the opponent could also move into this turn -- landing on one
        # risks a head-on collision that kills both bots.
        opponent_reachable = {loc for _, loc in neighbors(other, occupied)}

        non_risky = [(m, loc) for m, loc in safe_moves if loc not in opponent_reachable]
        candidate_moves = non_risky if non_risky else safe_moves

        best_move, best_score = candidate_moves[0][0], float('-inf')

        # Iterative deepening: start shallow, go deeper while time remains.
        # The result of the last *complete* depth is always kept, even if
        # a deeper pass gets interrupted partway through.
        for max_depth in range(2, 9, 2):  # 2, 4, 6, 8 moves
            if time.time() - start_time > TIME_BUDGET:
                break
            depth_best_move, depth_best_score = None, float('-inf')
            for move, new_loc in candidate_moves:
                if time.time() - start_time > TIME_BUDGET:
                    depth_best_move = None  # incomplete pass, discard it
                    break
                occupied.add(new_loc)
                score = minimax(new_loc, other, occupied, max_depth - 1, False,
                                 float('-inf'), float('inf'))
                occupied.remove(new_loc)
                if score > depth_best_score:
                    depth_best_move, depth_best_score = move, score
            if depth_best_move is not None:
                best_move, best_score = depth_best_move, depth_best_score

        # Final safety check: never return a move that isn't safe *right
        # now*, no matter what happened upstream in the search.
        x, y = me[0] + best_move.dx, me[1] + best_move.dy
        if not (0 <= x < state.width and 0 <= y < state.height) or (x, y) in state.walls:
            for m, _ in safe_moves:
                return m
            return Move.UP

        return best_move

if __name__ == "__main__":
    from games.tron import TronView
    from typing import FrozenSet
    state = TronView (
        self_id="1",
        width=21,
        height=21,
        turn=0,
        positions={"1": (2,10), "2":(18,10)},
        alive=["1", "2"],
        walls=frozenset(tuple(w) for w in [(2,10),(18,10)]),
    )
    print(state)

    bot = ExampleBot()
    print(bot.decide(state))