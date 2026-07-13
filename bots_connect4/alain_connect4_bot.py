"""Reference bot for Connect Four -- shows the minimum needed to
implement the Bot API against a ConnectFourView.

Strategy: play a winning move if one exists right now; otherwise block
the opponent's immediate winning move if they have one; otherwise play
the leftmost legal column. This is a shallow, one-ply heuristic with no
real lookahead -- it will lose to anything that actually searches the
game tree a few moves deep (minimax, ideally with alpha-beta pruning
and a transposition table so repeated positions aren't re-explored).
"""
from engine.bot import Bot


def _drop_row(board, column):
    """Row a piece would land on in `column`, or None if the column is full."""
    for row in range(len(board) - 1, -1, -1):
        if board[row][column] is None:
            return row
    return None


def _wins_at(board, row, column, player):
    height, width = len(board), len(board[0])
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        count = 1
        for sign in (1, -1):
            r, c = row + dr * sign, column + dc * sign
            while 0 <= r < height and 0 <= c < width and board[r][c] == player:
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 4:
            return True
    return False


def _would_win(board, column, player):
    row = _drop_row(board, column)
    if row is None:
        return False
    trial = [list(r) for r in board]
    trial[row][column] = player
    return _wins_at(trial, row, column, player)


class ExampleConnect4Bot(Bot):
    def decide(self, state) -> int:
        for column in state.legal_columns:
            if _would_win(state.board, column, state.self_id):
                return column

        for column in state.legal_columns:
            if _would_win(state.board, column, state.opponent_id):
                return column

        # Choose column with the "best" neighbouring
        best_score = 0
        best_column = -1
        for column in state.legal_columns:
            row = _drop_row(state.board, column)
            if row:
                score = 0
                for r,c in [(row+1, column-1), (row+1, column), (row+1, column+1), (row, column-1), (row, column+1), (row-1, column-1), (row-1, column), (row-1, column+1)]:
                    score += 1 if (0 <= r < state.height and 0 <= c < state.width and state.board[r][c] == state.self_id) else 0
                if score > best_score:
                    best_score = score
                    best_column = column
        if best_column >= 0:
            return best_column

        # play the center-most legal column
        return state.legal_columns[len(state.legal_columns)//2]
