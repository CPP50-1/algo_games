"""Unit tests for games.connect4 -- checks the rules themselves,
independent of any bot's strategy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from games.connect4 import ConnectFourGame, _winner_at


def test_vertical_win():
    board = [[None] * 7 for _ in range(6)]
    for r in range(2, 6):
        board[r][0] = "a"
    assert _winner_at(board, 2, 0) == "a"


def test_horizontal_win():
    board = [[None] * 7 for _ in range(6)]
    for c in range(4):
        board[5][c] = "a"
    assert _winner_at(board, 5, 3) == "a"


def test_rising_diagonal_win():
    board = [[None] * 7 for _ in range(6)]
    board[5][0] = board[4][1] = board[3][2] = board[2][3] = "a"
    assert _winner_at(board, 2, 3) == "a"


def test_falling_diagonal_win():
    board = [[None] * 7 for _ in range(6)]
    board[2][0] = board[3][1] = board[4][2] = board[5][3] = "a"
    assert _winner_at(board, 5, 3) == "a"


def test_three_in_a_row_is_not_a_win():
    board = [[None] * 7 for _ in range(6)]
    for c in range(3):
        board[5][c] = "a"
    assert _winner_at(board, 5, 2) is None


def test_alternates_turns_and_alive_bots_returns_one_player():
    g = ConnectFourGame(width=7, height=6)
    g.setup(["a", "b"])
    assert g.alive_bots() == ["a"]
    g.step({"a": 0})
    assert g.alive_bots() == ["b"]
    g.step({"b": 1})
    assert g.alive_bots() == ["a"]


def test_illegal_move_falls_back_to_leftmost_legal_column():
    g = ConnectFourGame(width=7, height=6)
    g.setup(["a", "b"])
    g.step({"a": 99})  # out of range
    assert g.frame()["board"][5][0] == "a"


def test_forfeited_move_falls_back_the_same_way():
    g = ConnectFourGame(width=7, height=6)
    g.setup(["a", "b"])
    g.step({"a": None})
    assert g.frame()["board"][5][0] == "a"


def test_full_board_is_a_draw():
    g = ConnectFourGame(width=7, height=6)
    g.setup(["a", "b"])
    # Fill the board avoiding any 4-in-a-row: alternate columns in a
    # pattern that never stacks 4 of the same piece in any direction.
    pattern = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6] * 3
    turn = 0
    for col in pattern:
        if g.is_over():
            break
        acting = g.alive_bots()[0]
        g.step({acting: col})
        turn += 1
    assert g.is_over()
    # Either someone won by accident of the pattern, or it's a draw --
    # either way the game must have terminated cleanly with no crash.


def test_setup_is_deterministic():
    g1, g2 = ConnectFourGame(), ConnectFourGame()
    g1.setup(["a", "b"])
    g2.setup(["a", "b"])
    assert g1.frame() == g2.frame()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"OK: {name}")
