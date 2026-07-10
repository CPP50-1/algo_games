import sys
import math
from engine.bot import Bot

def _render_board(state) -> str:
    symbol_for = {
        None: ".",
        state.self_id: "X",
        state.opponent_id: "O",
    }
    legal_columns = set(state.legal_columns)
    lines = ["    " + " ".join(f"{col:^3}" for col in range(state.width))]
    lines.append("   +" + "---+" * state.width)
    for row_index, row in enumerate(state.board):
        rendered_row = " | ".join(symbol_for.get(cell, "?") for cell in row)
        legal_marker = (
            "*"
            if any(col in legal_columns for col, cell in enumerate(row) if cell is None)
            else " "
        )
        lines.append(f"{row_index:>2}{legal_marker}| {rendered_row} |")
        lines.append("   +" + "---+" * state.width)
    lines.append(
        "    "
        + " ".join(
            " ^ " if col in legal_columns else "   " for col in range(state.width)
        )
    )
    return "\n".join(lines)

def _drop_row(board, column):
    for row in range(len(board) - 1, -1, -1):
        if board[row][column] is None: 
            return row
    return None

def winning_move(board, piece):
    ROWS = len(board)
    COLS = len(board[0])
    
    for c in range(COLS - 3):
        for r in range(ROWS):
            if board[r][c] == piece and board[r][c+1] == piece and board[r][c+2] == piece and board[r][c+3] == piece:
                return True
    for c in range(COLS):
        for r in range(ROWS - 3):
            if board[r][c] == piece and board[r+1][c] == piece and board[r+2][c] == piece and board[r+3][c] == piece:
                return True
    for c in range(COLS - 3):
        for r in range(3, ROWS):
            if board[r][c] == piece and board[r-1][c+1] == piece and board[r-2][c+2] == piece and board[r-3][c+3] == piece:
                return True
    for c in range(COLS - 3):
        for r in range(ROWS - 3):
            if board[r][c] == piece and board[r+1][c+1] == piece and board[r+2][c+2] == piece and board[r+3][c+3] == piece:
                return True
    return False

def evaluate_window(window, self_id, opponent_id):
    score = 0
    self_count = window.count(self_id)
    opp_count = window.count(opponent_id)
    empty_count = window.count(None) 

    if self_count == 3 and empty_count == 1:
        score += 1000
    elif self_count == 2 and empty_count == 2:
        score += 10
    elif self_count == 1 and empty_count == 3:
        score += 1

    if opp_count == 3 and empty_count == 1:
        score -= 1000
    elif opp_count == 2 and empty_count == 2:
        score -= 10
    elif opp_count == 1 and empty_count == 3:
        score -= 1

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
        # On peut sereinement passer à 5 grâce à la mémoire
        self.depth = 11
        # Notre Table de Transposition
        self.tt = {}

    def minimax(self, board, depth, alpha, beta, maximizing_player, self_id, opponent_id):
        # ---------------------------------------------------------
        # 1. LA MÉMOIRE (Recherche dans la Table de Transposition)
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
        # 2. LA SAUVEGARDE (Mise en cache du résultat avant de retourner)
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
        # Nettoyage de la RAM : si la mémoire stocke trop de grilles, on la vide
        # pour éviter que ton PC ne sature en tournoi long.
        if len(self.tt) > 500000:
            self.tt.clear()

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
            return state.legal_columns[0]
            
        return best_col