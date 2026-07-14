"""
Simple improvement on the base bot : will try to fill the center 3 first.
Yeah that's not good enough for anything more
"""
import sys
from math import ceil, floor

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


class VictorConnect4Bot(Bot):
    def decide(self, state) -> int:
        for column in state.legal_columns:
            if _would_win(state.board, column, state.self_id):
                return column

        for column in state.legal_columns:
            if _would_win(state.board, column, state.opponent_id):
                return column

        center = floor(state.width/2)
        if state.turn == 0 or (state.turn == 1 and _drop_row(state.board, center)):
            return center
        center_playing_row = _drop_row(state.board, center)+1
        center_last_player = state.board[center_playing_row][center]
        if center_last_player == state.self_id:
            for i in [-1, 1]:
                if state.board[center_playing_row][center + i] is None:
                    return center + i

        return state.legal_columns[0]