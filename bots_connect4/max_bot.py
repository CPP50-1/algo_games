"""
max_bot (connect4): bitboard negamax with alpha-beta pruning,
transposition table, time-budgeted iterative deepening, and a pattern-
aware heuristic.

Why bitboards matter:
  - Win checks are 4 shift-and-mask ops, not nested loops over the board.
  - Move gen is 7 column-height comparisons.
  - Board copy is 2 ints, not a 2D list copy.
  - The TT key (two bitboards) is a 2-int tuple — no hashing overhead.

Key features:
  - Time budget: a hard deadline stops mid-search gracefully via
    _SearchTimeout — no risk of engine timeout or crash.
  - Iterative deepening: deeper search re-uses the TT from shallower
    passes, so each extra depth costs much less than the first.
  - Dynamic move ordering: block opponent wins first, then build our
    threats (3/2-in-a-row), then centre bias as tiebreaker.
  - Heuristic: counts 2- and 3-in-a-row patterns on the bitboard
    instead of just centre-column pieces.
"""
import time
from engine.bot import Bot

COLS = 7
ROWS = 6
BITS = 7
MAX_MOVES = 42
INF = float("inf")
TIME_BUDGET = 0.08

H = 7
V = 1
DR = 8
DL = 6

EXACT, LOWER, UPPER = range(3)

WIN = 1_000_000


class _SearchTimeout(Exception):
    pass


class MaxBot(Bot):
    def __init__(self):
        super().__init__()
        self.tt = {}

    def decide(self, state) -> int:
        our_bb, opp_bb, height, moves_made = self._bitboard(state)
        legal = list(state.legal_columns)
        if len(legal) == 1:
            return legal[0]

        self.tt.clear()
        deadline = time.monotonic() + TIME_BUDGET
        remaining = MAX_MOVES - moves_made
        best = legal[0]

        try:
            for depth in range(1, remaining + 1):
                col, _ = self._negamax(
                    our_bb, opp_bb, height[:], depth, -INF, INF, deadline,
                )
                if col != -1:
                    best = col
        except _SearchTimeout:
            pass

        return best

    # ------------------------------------------------------------------
    # Board helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bitboard(state):
        our = opp = 0
        h = [0] * COLS
        n = 0
        for r in range(ROWS):
            for c in range(COLS):
                v = state.board[r][c]
                if v is None:
                    continue
                bit = 1 << (c * BITS + r)
                if v == state.self_id:
                    our |= bit
                else:
                    opp |= bit
                h[c] = r + 1
                n += 1
        return our, opp, h, n

    @staticmethod
    def _has_won(bb):
        m = bb & (bb >> H)
        if m & (m >> (2 * H)):
            return True
        m = bb & (bb >> V)
        if m & (m >> (2 * V)):
            return True
        m = bb & (bb >> DR)
        if m & (m >> (2 * DR)):
            return True
        m = bb & (bb >> DL)
        if m & (m >> (2 * DL)):
            return True
        return False

    @staticmethod
    def _consecutive(bb, bit, shift):
        count = 0
        pos = bit + shift
        while 0 <= pos < 64 and (bb >> pos) & 1:
            count += 1
            pos += shift
        return count

    def _col_score(self, bb, col, row):
        bit = col * BITS + row
        score = 0
        for shift in (H, V, DR, DL):
            total = 1 + self._consecutive(bb, bit, shift) + self._consecutive(bb, bit, -shift)
            if total >= 4:
                score += 1000
            elif total == 3:
                score += 100
            elif total == 2:
                score += 10
        return score

    def _order_moves(self, our_bb, opp_bb, height, legal):
        scored = []
        for c in legal:
            row = height[c]
            pos_bit = 1 << (c * BITS + row)
            block = self._has_won(opp_bb | pos_bit)
            block_score = 100000 if block else 0
            threat = self._col_score(our_bb, c, row)
            centre = 7 - abs(c - 3)
            scored.append((block_score + threat + centre, c))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored]

    # ------------------------------------------------------------------
    # Heuristic (leaf-node fallback)
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate(our_bb, opp_bb):
        """Count 2- and 3-in-a-row patterns via bitboard shifts."""
        score = 0
        for shift in (H, V, DR, DL):
            three = our_bb & (our_bb >> shift) & (our_bb >> (2 * shift))
            score += three.bit_count() * 50
            two = (our_bb & (our_bb >> shift)) ^ three
            score += two.bit_count() * 10
            opp_three = opp_bb & (opp_bb >> shift) & (opp_bb >> (2 * shift))
            score -= opp_three.bit_count() * 50
            opp_two = (opp_bb & (opp_bb >> shift)) ^ opp_three
            score -= opp_two.bit_count() * 10
        return score

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _negamax(self, our_bb, opp_bb, height, depth, alpha, beta, deadline):
        if time.monotonic() > deadline:
            raise _SearchTimeout()

        alpha_orig = alpha
        key = (our_bb, opp_bb)

        entry = self.tt.get(key)
        if entry is not None:
            d, s, flag = entry
            if d >= depth:
                if flag == EXACT:
                    return -1, s
                if flag == LOWER:
                    alpha = max(alpha, s)
                elif flag == UPPER:
                    beta = min(beta, s)
                if alpha >= beta:
                    return -1, s

        if self._has_won(opp_bb):
            return -1, -(WIN + 1 - depth)

        legal = [c for c in range(COLS) if height[c] < ROWS]
        if not legal:
            return -1, 0

        for c in legal:
            new_bb = our_bb | (1 << (c * BITS + height[c]))
            if self._has_won(new_bb):
                return c, WIN + 2 - depth

        if depth == 0:
            return legal[0], self._evaluate(our_bb, opp_bb)

        ordered = self._order_moves(our_bb, opp_bb, height, legal)
        best_col = ordered[0]

        for c in ordered:
            new_bb = our_bb | (1 << (c * BITS + height[c]))
            h2 = height[:]
            h2[c] += 1
            _, score = self._negamax(opp_bb, new_bb, h2, depth - 1, -beta, -alpha, deadline)
            score = -score
            if score > alpha:
                alpha = score
                best_col = c
            if alpha >= beta:
                break

        if alpha >= beta:
            self.tt[key] = (depth, alpha, LOWER)
        elif alpha > alpha_orig:
            self.tt[key] = (depth, alpha, EXACT)
        else:
            self.tt[key] = (depth, alpha, UPPER)

        return best_col, alpha
