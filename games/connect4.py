"""Connect Four.

Two bots alternate dropping a piece into a column; pieces fall to the
lowest empty row in that column. First to connect four in a row --
horizontally, vertically, or diagonally -- wins. Board full with no
winner is a draw.

This is a genuinely different shape of game from Tron or delivery: it's
turn-based, not simultaneous, and it's adversarial with perfect
information and no randomness at all. The entire game state is a 7x6
grid of three possible values per cell -- small enough to search deeply
in the time budget, which is exactly the point: a bot that only checks
"can I win this move / can I block an immediate threat" (a shallow
heuristic) will regularly lose to a bot that looks a few moves ahead
with minimax (optionally with alpha-beta pruning and a transposition
table / memoization to avoid re-exploring the same board position
reached via a different move order).

Turn handling: unlike Tron/delivery, only one bot acts per turn.
`alive_bots()` returns a single-element list -- whichever bot is "to
move" -- rather than every bot still in the match. This means the
engine's per-turn sandbox loop naturally only spends a subprocess call
on the player whose move actually matters, without any special-casing
in engine/match.py.

Actions are plain column indices (0-based, left to right), not the
Move enum -- decide() should return an int. This is exactly the case
serialize_action/deserialize_action exist for.

State handed to the acting bot's decide() is a `ConnectFourView`:
    self_id       -- your bot id
    opponent_id   -- the other bot id
    width, height -- board dimensions (7x6 by default)
    board         -- height x width grid, row 0 is the TOP row; each
                     cell is your bot id, the opponent's bot id, or None
    legal_columns -- columns that aren't full yet, in order
    turn          -- turn number (also how many pieces are on the board)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from games.base import Game

Board = List[List[Optional[str]]]


@dataclass(frozen=True)
class ConnectFourView:
    self_id: str
    opponent_id: str
    width: int
    height: int
    board: Tuple[Tuple[Optional[str], ...], ...]
    legal_columns: Tuple[int, ...]
    turn: int


def _winner_at(board: Board, row: int, col: int) -> Optional[str]:
    """Checks all four directions through (row, col) for a run of 4.
    Called only from the cell that was just played, so it only needs to
    check lines passing through that one cell, not the whole board."""
    player = board[row][col]
    if player is None:
        return None
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
            return player
    return None


class ConnectFourGame(Game):
    def __init__(self, width: int = 7, height: int = 6) -> None:
        self.width = width
        self.height = height
        self._board: Board = []
        self._bot_ids: List[str] = []
        self._turn = 0
        self._to_move = 0
        self._winner: Optional[str] = None
        self._draw = False

    def setup(self, bot_ids: List[str]) -> None:
        if len(bot_ids) != 2:
            raise ValueError("Connect Four is a 2-player game")
        self._bot_ids = list(bot_ids)
        self._board = [[None] * self.width for _ in range(self.height)]
        self._turn = 0
        self._to_move = 0  # bot_ids[0] always goes first -- see round_robin's
                            # side-swap, which plays this pairing both ways
        self._winner = None
        self._draw = False

    def _legal_columns(self) -> Tuple[int, ...]:
        return tuple(c for c in range(self.width) if self._board[0][c] is None)

    def view_for(self, bot_id: str) -> ConnectFourView:
        opponent = next(b for b in self._bot_ids if b != bot_id)
        return ConnectFourView(
            self_id=bot_id,
            opponent_id=opponent,
            width=self.width,
            height=self.height,
            board=tuple(tuple(row) for row in self._board),
            legal_columns=self._legal_columns(),
            turn=self._turn,
        )

    def step(self, moves: Dict[str, Optional[int]]) -> None:
        acting_bot = self._bot_ids[self._to_move]
        column = moves.get(acting_bot)
        legal = self._legal_columns()

        if not isinstance(column, int) or column not in legal:
            # Forfeited or illegal move: play the leftmost legal column
            # instead of ending the match over a single bad turn -- one
            # timeout or bug shouldn't be an instant loss, the same
            # philosophy as Tron's "keep going straight".
            column = legal[0]

        row = max(r for r in range(self.height) if self._board[r][column] is None)
        self._board[row][column] = acting_bot
        self._turn += 1

        won_by = _winner_at(self._board, row, column)
        if won_by:
            self._winner = won_by
        elif not self._legal_columns():
            self._draw = True
        else:
            self._to_move = 1 - self._to_move

    def alive_bots(self) -> List[str]:
        if self.is_over():
            return []
        return [self._bot_ids[self._to_move]]

    def is_over(self) -> bool:
        return self._winner is not None or self._draw

    def winners(self) -> List[str]:
        return [self._winner] if self._winner else []

    def frame(self) -> Dict:
        return {
            "turn": self._turn,
            "width": self.width,
            "height": self.height,
            "board": [[cell for cell in row] for row in self._board],
            "to_move": self._bot_ids[self._to_move] if not self.is_over() else None,
            "winner": self._winner,
            "draw": self._draw,
        }

    def serialize_view(self, view: ConnectFourView) -> Dict:
        return {
            "self_id": view.self_id,
            "opponent_id": view.opponent_id,
            "width": view.width,
            "height": view.height,
            "board": [list(row) for row in view.board],
            "legal_columns": list(view.legal_columns),
            "turn": view.turn,
        }

    @staticmethod
    def deserialize_view(data: Dict) -> ConnectFourView:
        return ConnectFourView(
            self_id=data["self_id"],
            opponent_id=data["opponent_id"],
            width=data["width"],
            height=data["height"],
            board=tuple(tuple(row) for row in data["board"]),
            legal_columns=tuple(data["legal_columns"]),
            turn=data["turn"],
        )

    @staticmethod
    def serialize_action(action) -> int:
        return int(action)  # raises for anything that isn't int-like -- treated as forfeit

    @staticmethod
    def deserialize_action(data) -> int:
        return int(data)
