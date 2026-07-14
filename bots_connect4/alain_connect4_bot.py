"""Reference bot for Connect Four -- shows the minimum needed to
implement the Bot API against a ConnectFourView.

Strategy: play a winning move if one exists right now; otherwise block
the opponent's immediate winning move if they have one; otherwise play
the leftmost legal column. This is a shallow, one-ply heuristic with no
real lookahead -- it will lose to anything that actually searches the
game tree a few moves deep (minimax, ideally with alpha-beta pruning
and a transposition table so repeated positions aren't re-explored).
"""
import sys

from engine.bot import Bot
from games.connect4 import ConnectFourView


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


class AlainConnect4Bot(Bot):
    def decide(self, state) -> int:
        # Check if we can win on this turn
        for column in state.legal_columns:
            if _would_win(state.board, column, state.self_id):
                return column

        # Check if the opponent can win on this turn. If yes, try to avoid it.
        for column in state.legal_columns:
            if _would_win(state.board, column, state.opponent_id):
                return column

        # Check if we could win on the next move against a stupid bot
        for column in state.legal_columns:
            row = _drop_row(state.board, column)
            next_board = [list(r) for r in state.board]
            if row:
                next_board[row][column] = state.self_id
                next_legal_columns = list(state.legal_columns)
                if row == 0: # top row, column would become illegal
                    next_legal_columns.remove(column)
                for col in next_legal_columns:
                    if _would_win(next_board, col, state.self_id):
                        return column

        # Choose column with the "best" neighborhood
        best_score = 0
        best_column = -1
        center_column = state.width//2
        for column in state.legal_columns:
            row = _drop_row(state.board, column)
            if row:
                score = 0
                for r,c in [(row+1, column-1), (row+1, column), (row+1, column+1), (row, column-1), (row, column+1), (row-1, column-1), (row-1, column), (row-1, column+1)]:
                    # a neighboring cell occupied by us is worth 3. an empty neighboring cell is worth 1
                    score += 0 if not (0 <= r < state.height and 0 <= c < state.width) \
                        else 3 if state.board[r][c] == state.self_id \
                        else 1 if state.board[r][c] is None \
                        else 0
                if score >= best_score:
                    best_score = score
                    # in case of equality, choose the one closest to the center column
                    if abs(column - center_column) < abs(best_column - center_column):
                        best_column = column

        if best_column >= 0:
            return best_column

        # If none of the above, play the center-most legal column
        return state.legal_columns[len(state.legal_columns)//2]


if __name__ == '__main__':
    bot = AlainConnect4Bot()
    bot.decide(ConnectFourView(self_id='alain_connect4_bot', opponent_id='example_connect4_bot', width=7, height=6,
                    board=((None, None, None, None, None, None, None), (None, None, None, None, None, None, None),
                           (None, None, None, None, None, None, None), (None, None, None, None, None, None, None),
                           (None, None, None, None, None, None, None), (None, None, None, None, None, None, None)),
                    legal_columns=(0, 1, 2, 3, 4, 5, 6), turn=0))