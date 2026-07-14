import sys
import math
import tempfile
from engine.bot import Bot

_LOG_PATH = tempfile.gettempdir() + "/theophile_connect4_bot.log"


def _log(message: str) -> None:
    with open(_LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")

def _render_board(state) -> str:
    symbol_for = {
        None: ".",
        state.self_id: "X",
        state.opponent_id: "O",
    }
    lines = ["    " + " ".join(f"{col:^3}" for col in range(state.width))]
    lines.append("   +" + "---+" * state.width)
    for row_index, row in enumerate(state.board):
        rendered_row = " | ".join(symbol_for.get(cell, "?") for cell in row)
        legal_marker = (
            "*"
            if any(col in state.legal_columns for col, cell in enumerate(row) if cell is None)
            else " "
        )
        lines.append(f"{row_index:>2}{legal_marker}| {rendered_row} |")
        lines.append("   +" + "---+" * state.width)
    lines.append(
        "    "
        + " ".join(
            " ^ " if col in state.legal_columns else "   " for col in range(state.width)
        )
    )
    return "\n".join(lines)

def _drop_row(board, column)-> int | None:
    """
    Return the lowest empty row index in ``column``.
    The board is expected to be a 2D list indexed as ``board[row][column]``
    with row 0 at the top. Returns ``None`` if the column is full.
    """
    
    for row in range(len(board) - 1, -1, -1):
        if board[row][column] is None: 
            return row
    return None

def winning_move(board, piece):
    """
    Return True if ``piece`` has four in a row on ``board``.

    The board is a 2D list indexed as ``board[row][column]`` with row 0
    at the top. The function checks horizontal, vertical, and both
    diagonal directions.
    """
    
    ROWS = len(board)
    COLS = len(board[0])
        
    # right (0,1), down (1,0), down-right (1,1), down-left (1,-1)'
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for row in range(ROWS):
        for col in range(COLS):
            if board[row][col] != piece:
                continue
            for dr, dc in directions:
                # Walk four cells in one direction and stop if any cell is
                # out of bounds or belongs to the other player.
                if all(
                        # row + k * dr / col + k * dc picks the next cell in
                        # the current direction, one step at a time.
                        # Stay inside the board horizontally and vertically.
                        0 <= row + k * dr < ROWS
                    and 0 <= col + k * dc < COLS
                    # Every cell in this line must belong to the same piece.
                    and board[row + k * dr][col + k * dc] == piece
                    for k in range(4)
                ):
                    return True
    return False

def evaluate_window(window, self_id, opponent_id):
    """Score a 4-cell window from the point of view of ``self_id``.

    Positive scores favor our pieces, negative scores favor the opponent.
    The score gets larger when a window is close to becoming four in a row
    and smaller when it helps the opponent do the same.
    """

    score = 0
    self_count = window.count(self_id)
    opp_count = window.count(opponent_id)
    empty_count = window.count(None)
    
    # (piece_count, empty_count)
    self_pattern_score = {
        (3, 1): 1000,
        (2, 2): 10,
        (1, 3): 1,
    }

    # Slightly stronger penalties make the bot prioritize blocking threats.
    opp_pattern_score = {
        (3, 1): 1000,
        (2, 2): 10,
        (1, 3): 1,
    }

    score += self_pattern_score.get((self_count, empty_count), 0)
    score -= opp_pattern_score.get((opp_count, empty_count), 0)

    return score

def evaluate_board(board, self_id, opponent_id):
    score = 0
    ROWS = len(board)
    COLS = len(board[0])

    center_array = [board[r][COLS//2] for r in range(ROWS)]
    score += center_array.count(self_id) * 3

    for r in range(ROWS):
        row_array = board[r]
        for c in range(COLS - 3):
            window = row_array[c:c+4]
            score += evaluate_window(window, self_id, opponent_id)

    for c in range(COLS):
        for r in range(ROWS - 3):
            window = [board[r+i][c] for i in range(4)]
            score += evaluate_window(window, self_id, opponent_id)

    for r in range(3, ROWS):
        for c in range(COLS - 3):
            window = [board[r-i][c+i] for i in range(4)]
            score += evaluate_window(window, self_id, opponent_id)

    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            window = [board[r+i][c+i] for i in range(4)]
            score += evaluate_window(window, self_id, opponent_id)

    return score

def is_terminal_node(board, self_id, opponent_id):
    if winning_move(board, self_id):
        return True, 10000000
    if winning_move(board, opponent_id):
        return True, -10000000
    if all(board[0][c] is not None for c in range(len(board[0]))):
        return True, 0
    return False, 0

class TheophileConnect4Bot(Bot):
    def __init__(self):
        self.depth = 6
        # Table de Transposition
        self.tt = {}
        _log("bot initialised")

    def minimax(self, board, depth, alpha, beta, maximizing_player, self_id, opponent_id):
        # ---------------------------------------------------------
        # 1. Table de Transposition
        # ---------------------------------------------------------
        original_alpha = alpha
        original_beta = beta
        
        # On convertit le tableau 2D mutable en Tuple immuable pour l'utiliser comme clé de dictionnaire
        board_tuple = tuple(tuple(row) for row in board)
        # On crée aussi la version miroir (inversée horizontalement)
        mirror_tuple = tuple(tuple(row[::-1]) for row in board)
        
        state_key = (board_tuple, maximizing_player)
        mirror_key = (mirror_tuple, maximizing_player)
        
        tt_entry = None
        is_mirrored = False
        
        # On regarde si on connaît déjà cette grille ou son jumeau miroir
        if state_key in self.tt:
            tt_entry = self.tt[state_key]
        elif mirror_key in self.tt:
            tt_entry = self.tt[mirror_key]
            is_mirrored = True
            
        # Si la mémoire est suffisante (profondeur égale ou supérieure)
        if tt_entry is not None and tt_entry['depth'] >= depth:
            if tt_entry['flag'] == 'EXACT':
                best_c = tt_entry['best_col']
                # Si on a trouvé la solution dans le miroir, il faut inverser la colonne à jouer !
                if is_mirrored and best_c is not None:
                    best_c = 6 - best_c
                return best_c, tt_entry['value']
                
            elif tt_entry['flag'] == 'LOWERBOUND':
                alpha = max(alpha, tt_entry['value'])
            elif tt_entry['flag'] == 'UPPERBOUND':
                beta = min(beta, tt_entry['value'])
                
            if alpha >= beta:
                best_c = tt_entry['best_col']
                if is_mirrored and best_c is not None:
                    best_c = 6 - best_c
                return best_c, tt_entry['value']
        # ---------------------------------------------------------

        valid_locations = [c for c in range(len(board[0])) if board[0][c] is None]
        center = len(board[0]) // 2
        valid_locations.sort(key=lambda x: abs(center - x))

        is_terminal, terminal_score = is_terminal_node(board, self_id, opponent_id)

        if depth == 0 or is_terminal:
            if is_terminal:
                return None, terminal_score
            else:
                return None, evaluate_board(board, self_id, opponent_id)

        if maximizing_player:
            value = -math.inf
            best_col = valid_locations[0] if valid_locations else None
            
            for col in valid_locations:
                row = _drop_row(board, col)
                board[row][col] = self_id 
                
                new_score = self.minimax(board, depth-1, alpha, beta, False, self_id, opponent_id)[1]
                board[row][col] = None 
                
                if new_score > value:
                    value = new_score
                    best_col = col
                alpha = max(alpha, value)
                if alpha >= beta:
                    break 
        else:
            value = math.inf
            best_col = valid_locations[0] if valid_locations else None
            
            for col in valid_locations:
                row = _drop_row(board, col)
                board[row][col] = opponent_id 
                
                new_score = self.minimax(board, depth-1, alpha, beta, True, self_id, opponent_id)[1]
                board[row][col] = None 
                
                if new_score < value:
                    value = new_score
                    best_col = col
                beta = min(beta, value)
                if alpha >= beta:
                    break 

        # ---------------------------------------------------------
        # 2. Mise en cache du résultat avant de retourner
        # ---------------------------------------------------------
        flag = 'EXACT'
        if value <= original_alpha:
            flag = 'UPPERBOUND'
        elif value >= original_beta:
            flag = 'LOWERBOUND'
            
        self.tt[state_key] = {
            'depth': depth,
            'value': value,
            'flag': flag,
            'best_col': best_col
        }
        # ---------------------------------------------------------

        return best_col, value

    def decide(self, state) -> int:
        # Nettoyage de la RAM
        if len(self.tt) > 500000:
            self.tt.clear()

        _log(f"turn={state.turn} self={state.self_id} opponent={state.opponent_id}")

        print(
            f"self={state.self_id} opponent={state.opponent_id} turn={state.turn}\n{_render_board(state)}",
            file=sys.stderr,
            flush=True,
        )

        if state.turn < 2:
            center = state.width // 2
            if center in state.legal_columns:
                return center

        mutable_board = [list(row) for row in state.board]

        best_col, score = self.minimax(
            mutable_board, 
            self.depth, 
            -math.inf, 
            math.inf, 
            True, 
            state.self_id, 
            state.opponent_id
        )
        
        if best_col is None or best_col not in state.legal_columns:
            _log(f"chosen={state.legal_columns[0]} reason=fallback")
            return state.legal_columns[0]
            
        _log(f"chosen={best_col} reason=minimax")
        return best_col