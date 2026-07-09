from engine.bot import Bot
import time


def _drop_row(board, column):
    pass
    # """Row a piece would land on in `column`, or None if the column is full."""
    # for row in range(len(board) - 1, -1, -1):
    #     if board[row][column] is None:
    #         return row
    # return None


def _wins_at(board, row, column, player):
    pass
    # height, width = len(board), len(board[0])
    # for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
    #     count = 1
    #     for sign in (1, -1):
    #         r, c = row + dr * sign, column + dc * sign
    #         while 0 <= r < height and 0 <= c < width and board[r][c] == player:
    #             count += 1
    #             r += dr * sign
    #             c += dc * sign
    #     if count >= 4:
    #         return True
    # return False


def _would_win(board, column, player):
    pass
    # row = _drop_row(board, column)
    # if row is None:
    #     return False
    # trial = [list(r) for r in board]
    # trial[row][column] = player
    # return _wins_at(trial, row, column, player)


class FexBot(Bot):

    def __init__(self):
        super().__init__()
        self.table = {}
        self.bottoms = [6, 13, 20, 27, 34, 41, 48] # starting "positions" of the bottom of each column
        self.ceilings = [0, 7, 14, 21, 28, 35, 42] # ceilings for each column (unplayable slots)
        self.mask = 0  # Read below. 0 represents emptiness, 1 represents a token. Combines with self.position.
        self.current_player_token = 0  # binary used as a boolean. Combine with self.mask to infer board state.
        """
        00 means empty; 01 is impossible; 10 means opponent has a token; 11 means current player has a token.
        The bits of these 64-digit long binary values represent the board state at any given time.
        For example, column 1 contains bits 1 to 6, with bit 0 acting as the ceiling (useful to mark full columns).
        Column 2 contains bits 8 (topmost) to 13 (bottom), with bit 7 acting as the ceiling. Here's a visualization:
        
                            00|07|14|21|28|35|42
                            --------------------
                            01|08|15|22|29|36|43
                            02|09|16|23|30|37|44
                            03|10|17|24|31|38|45
                            04|11|18|25|32|39|46
                            05|12|19|26|33|40|47
                            06|13|20|27|34|41|48
                                                
        If for example the 27th digit of the mask is 1 and the 6th digit of the current_player_token is 0,
        it means that the bottom center slot of the game board contains a token played by the opponent.
        """

    def is_full(self, col):
        return self.bottoms[col] == self.ceilings[col]

    def explore_possible_moves(self, state):
        # Here comes the recursive minimaxing and alpha-bêta pruning.
        pass

    def decide(self, state) -> int:
        for column in state.legal_columns:
            if _would_win(state.board, column, state.self_id):
                return column

        for column in state.legal_columns:
            if _would_win(state.board, column, state.opponent_id):
                return column

        # return self.explore_possible_moves(state)

        # dummy return to prevent squiggly underlining. todo remove
        return state.legal_columns[len(state.legal_columns) / 2]

