"""Connect Four bot -- negamax with alpha-beta pruning, a transposition
table, and iterative deepening under a time budget, instead of the
one-ply "win now / block now" heuristic the reference bot uses.

Why the reference bot loses: it only ever looks at *this* move. It
correctly takes an immediate win and blocks an immediate threat, but it
has no idea that playing column 3 now creates a fork two moves later
that it can't stop, because it never simulates the opponent's reply to
its own reply. Any real lookahead beats that consistently.

Search design:
  - negamax: minimax written in the single-perspective form, where
    each recursive call returns a score *from the point of view of
    whoever is about to move at that node*, and the caller negates the
    child's value to flip perspective going back up. Equivalent to
    plain minimax, just less code duplication between the maximizing
    and minimizing cases.
  - alpha-beta pruning: once a branch is proven worse than a line the
    opponent could already force elsewhere, stop exploring it -- the
    result can't change, so there's no point computing it.
  - transposition table (memoization): the same board can be reached
    by different move orders (e.g. col 2 then col 4 vs. col 4 then
    col 2). It's cached by board content, keyed with the depth it was
    searched to, so a shallower repeat lookup can reuse it and a
    deeper one knows to re-search. Whose turn it is at a given board is
    fully determined by the piece count on it, so the board alone is
    an unambiguous key -- no need to store the side to move separately.
  - iterative deepening: search depth 1, then 2, then 3, ... re-using
    the transposition table between passes, until a wall-clock budget
    runs out. This is what makes the bot safe under a hard per-move
    timeout: it always has *some* best move ready (from the last fully
    completed depth) even if it gets cut off mid-search on the next
    one, rather than gambling everything on one fixed search depth
    that might not finish in time on a slower position.
  - move ordering: center columns first. Center columns take part in
    more possible four-in-a-rows, so they tend to be the strongest
    moves -- searching them first lets alpha-beta prune far more of
    the tree than a naive left-to-right order would.
  - static evaluation (used only when the time budget runs out before
    a branch reaches a win/loss/draw): counts open three-in-a-rows and
    two-in-a-rows for each side across every possible four-window on
    the board, plus a small bonus for center-column control. This is
    what the search falls back on instead of guessing "0" for
    positions it couldn't fully resolve.
"""
import time

from engine.bot import Bot

WIN_SCORE = 1_000_000
_EXACT, _LOWER, _UPPER = 0, 1, 2


class _SearchTimeout(Exception):
    """Raised to unwind the search the instant the time budget is up."""


def _drop_row(board, column):
    for row in range(len(board) - 1, -1, -1):
        if board[row][column] is None:
            return row
    return None


def _wins_at(board, row, col, player):
    height, width = len(board), len(board[0])
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        count = 1
        for sign in (1, -1):
            r, c = row + dr * sign, col + dc * sign
            while 0 <= r < height and 0 <= c < width and board[r][c] == player:
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 4:
            return True
    return False


def _apply(board, column, player):
    row = _drop_row(board, column)
    new_rows = [list(r) for r in board]
    new_rows[row][column] = player
    return tuple(tuple(r) for r in new_rows), row


def _legal_columns(board):
    return [c for c in range(len(board[0])) if board[0][c] is None]


def _ordered_columns(legal, width):
    center = width // 2
    return sorted(legal, key=lambda c: abs(c - center))


def _window_score(cells, self_id, opp_id):
    self_count = cells.count(self_id)
    opp_count = cells.count(opp_id)
    if self_count and opp_count:
        return 0  # contested window -- neither side can complete four here
    if self_count == 3:
        return 50
    if self_count == 2:
        return 10
    if opp_count == 3:
        return -50
    if opp_count == 2:
        return -10
    return 0


def _evaluate(board, self_id, opp_id):
    """Heuristic score from `self_id`'s perspective for a non-terminal
    position the search couldn't resolve within its time/depth budget.
    """
    height, width = len(board), len(board[0])
    score = 0

    center = width // 2
    score += 3 * sum(1 for r in range(height) if board[r][center] == self_id)
    score -= 3 * sum(1 for r in range(height) if board[r][center] == opp_id)

    for r in range(height):
        for c in range(width - 3):
            score += _window_score([board[r][c + i] for i in range(4)], self_id, opp_id)
    for c in range(width):
        for r in range(height - 3):
            score += _window_score([board[r + i][c] for i in range(4)], self_id, opp_id)
    for r in range(height - 3):
        for c in range(width - 3):
            score += _window_score([board[r + i][c + i] for i in range(4)], self_id, opp_id)
    for r in range(3, height):
        for c in range(width - 3):
            score += _window_score([board[r - i][c + i] for i in range(4)], self_id, opp_id)

    return score


def _negamax(board, depth, alpha, beta, player, opponent, ply, deadline, tt, width):
    if time.monotonic() > deadline:
        raise _SearchTimeout()

    entry = tt.get(board)
    original_alpha = alpha
    if entry is not None and entry[0] >= depth:
        e_depth, e_value, e_flag, e_move = entry
        if e_flag == _EXACT:
            return e_value, e_move
        if e_flag == _LOWER:
            alpha = max(alpha, e_value)
        elif e_flag == _UPPER:
            beta = min(beta, e_value)
        if alpha >= beta:
            return e_value, e_move

    if depth == 0:
        return _evaluate(board, player, opponent), None

    legal = _legal_columns(board)
    if not legal:
        return 0, None  # full board, no winner -- draw

    best_value = -WIN_SCORE - 1
    best_move = None
    for column in _ordered_columns(legal, width):
        child, row = _apply(board, column, player)
        if _wins_at(child, row, column, player):
            # Prefer a quicker win over a slower one: subtract ply so a
            # forced win found sooner scores strictly higher than one
            # found deeper in the tree.
            value = WIN_SCORE - ply
        elif not _legal_columns(child):
            value = 0  # this move fills the board with no winner
        else:
            child_value, _ = _negamax(
                child, depth - 1, -beta, -alpha, opponent, player, ply + 1, deadline, tt, width
            )
            value = -child_value

        if value > best_value:
            best_value = value
            best_move = column
        if value > alpha:
            alpha = value
        if alpha >= beta:
            break  # beta cutoff -- opponent already has a better option elsewhere

    if best_value <= original_alpha:
        flag = _UPPER
    elif best_value >= beta:
        flag = _LOWER
    else:
        flag = _EXACT
    tt[board] = (depth, best_value, flag, best_move)
    return best_value, best_move


class DenisConnect4Bot(Bot):
    # The sandbox's timeout is a wall-clock budget on the *whole*
    # subprocess call, not just the time spent inside decide() -- every
    # call pays for spawning a fresh Python interpreter plus JSON
    # (de)serialization, measured at ~60-70ms on its own here, and that
    # overhead is itself subject to OS scheduling jitter, not a fixed
    # cost. Budgeting right up to "0.2s minus the measured overhead"
    # leaves no room for that jitter and risks the subprocess getting
    # killed mid-search -- which forfeits the turn (leftmost column),
    # often a far worse outcome than stopping one iterative-deepening
    # pass earlier would have been. This stays well clear of that edge.
    TIME_LIMIT = 0.08

    def decide(self, state) -> int:
        legal = list(state.legal_columns)
        if len(legal) == 1:
            return legal[0]

        board = state.board
        width = state.width
        self_id, opp_id = state.self_id, state.opponent_id
        deadline = time.monotonic() + self.TIME_LIMIT

        tt = {}
        best_move = _ordered_columns(legal, width)[0]  # center-ish fallback if depth 1 somehow doesn't finish
        max_depth = width * len(board)  # a full board's worth of plies is a hard ceiling

        depth = 1
        try:
            while depth <= max_depth:
                value, move = _negamax(
                    board, depth, -WIN_SCORE - 1, WIN_SCORE + 1, self_id, opp_id, state.turn, deadline, tt, width
                )
                if move is not None:
                    best_move = move
                if abs(value) >= WIN_SCORE - 1000:
                    break  # forced win or loss found within the horizon -- deeper search won't change the decision
                depth += 1
        except _SearchTimeout:
            pass  # keep whatever best_move came from the last depth that finished in time

        return best_move

if __name__ == "__main__":
    def coups_possibles(allumettes):
        return [coup for coup in (1, 2, 3) if coup <= allumettes]
    def position_terminale(allumettes):
        return allumettes == 0
    def evaluer(allumettes):
        if allumettes == 0:
            return -1
        return 0
    def negamax(position, profondeur):
        if position_terminale(position) or profondeur == 0:
            return evaluer(position)
        meilleur_score = float("-inf")
        for coup in coups_possibles(position):
            position_suivante = position - coup
            score = -negamax(position_suivante, profondeur - 1)
            meilleur_score = max(meilleur_score, score)
        return meilleur_score
    def meilleur_coup(allumettes):
        meilleur_score = float("-inf")
        meilleur = None
        for coup in coups_possibles(allumettes):
            score = -negamax(allumettes - coup, 5)
            if score > meilleur_score:
                meilleur_score = score
                meilleur = coup
        return meilleur, meilleur_score

    for n in range(1, 11):
        print(n, negamax(n,5))

    print(meilleur_coup(10))