from pathlib import Path
from engine.bot import Bot
import time
import json
from typing import Any


class FexBot(Bot):
    def __init__(self):
        super().__init__()
        # binary representation of the board's valid tiles. 0s are used to prevent overflow from one column to the next.
        self.board_mask = 0b0111111_0111111_0111111_0111111_0111111_0111111_0111111
        # order of columns to default to (for optimal play search, default behaviors, etc.)
        self.static_order = [3, 2, 4, 1, 5, 0, 6]
        # dummy values to initialize the properties with their types.
        self.all_tokens = 0
        self.current_player_tokens = 0
        self.table = {}
        self.start_time = 0.0
        # optimized collection of opening moves to save resources on the first few turns (Connect 4 is a solved game)
        self.opening_book = {
            # first turn when going first
            "0,0": 3,

            #second turn when going first
            "6291456,2097152": 3,
            "2113536,2097152": 3,
            "35667968,2097152": 3,
            "2097168,2097152": 2,
            "69206016,2097152": 4,
            "2097153,2097152": 2,
            "538968064,2097152": 4,

            # third turn when going first
            "31457280,14680064": 3,
            "22036480,14680064": 3,
            "55574528,14680064": 3,
            "6307840,6291456": 3,

            # == Going second ==

            # first turn when going second
            "2097152,0": 3,
            "14,0": 3,
            "16384,0": 3,
            "274877906944,0": 3,

            # second turn when going second
            "14680064,4194304": 3,
            "6307840,4194304": 2,
            "274726912,4194304": 4,
            "4210688,4194304": 3,
            "71303168,4194304": 3
        }

    def sync_bitboard(self, state: Any) -> None:
        """Converts the 2D array-formatted board into bit integers"""
        self.all_tokens = 0
        self.current_player_tokens = 0
        my_id = str(state.self_id)
        for row in range(state.height):
            for col in range(state.width):
                cell_value = state.board[row][col]
                if cell_value is not None:
                    bitboard_row = (state.height - 1) - row
                    bit_index = (col * 7) + bitboard_row
                    self.all_tokens |= (1 << bit_index)
                    if str(cell_value) == my_id:
                        self.current_player_tokens |= (1 << bit_index)

    def check_win(self, position: int) -> bool:
        """Checks for wins in all 4 directions"""
        valid_pos = position & self.board_mask
        if valid_pos & (valid_pos >> 1) & (valid_pos >> 2)  & (valid_pos >> 3) : return True # horizontal
        if valid_pos & (valid_pos >> 7) & (valid_pos >> 14) & (valid_pos >> 21): return True # vertical
        if valid_pos & (valid_pos >> 6) & (valid_pos >> 12) & (valid_pos >> 18): return True # \ diagonal
        if valid_pos & (valid_pos >> 8) & (valid_pos >> 16) & (valid_pos >> 24): return True # / diagonal
        return False

    def alpha_beta(self, active: int, waiting: int, ply: int, max_depth: int, alpha: float, beta: float) -> float:
        """Negamax engine with a local lookup dictionary to avoid computing the same state multiple times per turn"""
        if time.time() - self.start_time > 0.88:
            raise TimeoutError

        remaining_depth = max_depth - ply

        # creates a 128-bit integer containing the positions of tokens played by each player as a unique combination
        lookup_key = (active << 64) | waiting
        # in order to speed up the process if it was tested before with a better depth than what's remaining
        if lookup_key in self.table:
            cached_depth, cached_value = self.table[lookup_key]
            if remaining_depth <= cached_depth:
                return cached_value

        if self.check_win(waiting):
            return -1000.0 + ply

        # show all tokens
        mask = active | waiting
        # if the recursion reached the current iteration's maximum depth of search
        # or if the playing field is full (meaning there is no next step to compute), we compute the scores.
        if ply == max_depth or (mask & self.board_mask) == self.board_mask:
            score = 0

            # extra emphasis on the center column, diminishing as we play to the sides
            mask_col3 = 0b1111111 << 21
            mask_col2_4 = (0b1111111 << 14) | (0b1111111 << 28)
            mask_col1_5 = (0b1111111 << 7) | (0b1111111 << 35)

            score += bin(active & mask_col3).count("1") * 100
            score -= bin(waiting & mask_col3).count("1") * 100
            score += bin(active & mask_col2_4).count("1") * 10
            score -= bin(waiting & mask_col2_4).count("1") * 10
            score += bin(active & mask_col1_5).count("1") * 4
            score -= bin(waiting & mask_col1_5).count("1") * 4

            # === Detection and filtering of valid, non-blocked length-3 lines ===
            # create a filter that contains only the game's empty tiles
            empty = ~mask & self.board_mask

            # horizontal length-3 lines (must have at least one unblocked open end to be valuable)
            th_active = active & (active >> 7) & (active >> 14)
            th_waiting = waiting & (waiting >> 7) & (waiting >> 14)

            h_left_us = (th_active >> 7) & empty
            h_right_us = (th_active << 21) & empty
            open_h_us = h_left_us & h_right_us
            single_h_us = (h_left_us | h_right_us) ^ open_h_us
            score += bin(single_h_us).count("1") * 35

            h_left_them = (th_waiting >> 7) & empty
            h_right_them = (th_waiting << 21) & empty
            open_h_them = h_left_them & h_right_them
            single_h_them = (h_left_them | h_right_them) ^ open_h_them
            score -= bin(single_h_them).count("1") * 35

            # / diagonal length-3 lines (must have at least one unblocked open end to be valuable)
            td1_active = active & (active >> 6) & (active >> 12)
            td1_waiting = waiting & (waiting >> 6) & (waiting >> 12)

            d1_left_us = (td1_active >> 6) & empty
            d1_right_us = (td1_active << 18) & empty
            open_d1_us = d1_left_us & d1_right_us
            single_d1_us = (d1_left_us | d1_right_us) ^ open_d1_us
            score += bin(single_d1_us).count("1") * 25

            d1_left_them = (td1_waiting >> 6) & empty
            d1_right_them = (td1_waiting << 18) & empty
            open_d1_them = d1_left_them & d1_right_them
            single_d1_them = (d1_left_them | d1_right_them) ^ open_d1_them
            score -= bin(single_d1_them).count("1") * 25

            # \ diagonal length-3 lines (must have at least one unblocked open end to be valuable)
            td2_active = active & (active >> 8) & (active >> 16)
            td2_waiting = waiting & (waiting >> 8) & (waiting >> 16)

            d2_left_us = (td2_active >> 8) & empty
            d2_right_us = (td2_active << 24) & empty
            open_d2_us = d2_left_us & d2_right_us
            single_d2_us = (d2_left_us | d2_right_us) ^ open_d2_us
            score += bin(single_d2_us).count("1") * 25

            d2_left_them = (td2_waiting >> 8) & empty
            d2_right_them = (td2_waiting << 24) & empty
            open_d2_them = d2_left_them & d2_right_them
            single_d2_them = (d2_left_them | d2_right_them) ^ open_d2_them
            score -= bin(single_d2_them).count("1") * 25

            # vertical length-3 lines (must have an open empty space above to ever achieve a Connect Four)
            tv_active = active & (active >> 1) & (active >> 2)
            tv_waiting = waiting & (waiting >> 1) & (waiting >> 2)
            score += bin((tv_active << 3) & empty).count("1") * 20
            score -= bin((tv_waiting << 3) & empty).count("1") * 20

            # === Detection and massive scoring of double-ended threats ===
            # find such horizontal lines
            score += bin(open_h_us).count("1") * 60
            score -= bin(open_h_them).count("1") * 60

            # find such / diagonal lines
            score += bin(open_d1_us).count("1") * 45
            score -= bin(open_d1_them).count("1") * 45

            # find such \ diagonal lines
            score += bin(open_d2_us).count("1") * 45
            score -= bin(open_d2_them).count("1") * 45

            # == Small bonuses for length-2 lines ==
            score += bin(active & (active >> 7)).count("1") * 8
            score += bin(active & (active << 7)).count("1") * 8
            score -= bin(waiting & (waiting >> 7)).count("1") * 8
            score -= bin(waiting & (waiting << 7)).count("1") * 8

            score += bin(active & (active >> 6)).count("1") * 5
            score += bin(active & (active << 6)).count("1") * 5
            score += bin(active & (active >> 8)).count("1") * 5
            score += bin(active & (active << 8)).count("1") * 5

            score -= bin(waiting & (waiting >> 6)).count("1") * 5
            score -= bin(waiting & (waiting << 6)).count("1") * 5
            score -= bin(waiting & (waiting >> 8)).count("1") * 5
            score -= bin(waiting & (waiting << 8)).count("1") * 5

            return float(score)

        max_value = float('-inf')

        # browse columns in order of priority
        for col in self.static_order:
            # avoid parsing full columns right away
            if not (mask & (1 << ((col * 7) + 5))):
                # check each tile of that column
                for row in range(6):
                    bit_index = (col * 7) + row
                    # if that tile is empty (else move one tile up, as per the loop we entered)
                    if not (mask & (1 << bit_index)):
                        # recursive call that inverts the result when it's the opponent's turn
                        # replaces the need for duplicating this loop at the cost of manually writing every move value twice in the code
                        # in turn, this allows us to weight every option differently if the need arises
                        value = -self.alpha_beta(waiting, active | (1 << bit_index), ply + 1, max_depth, -beta, -alpha)
                        if value > max_value:
                            max_value = value
                        if value > alpha:
                            alpha = value
                        break
                if beta <= alpha:
                    break
        # add the current check in the table for future reference this turn
        self.table[lookup_key] = [remaining_depth, max_value]
        return max_value

    def decide(self, state: Any) -> int:
        try:
            # create a unique file path in the temporary directory (/tmp) for this specific bot instance
            scratch = Path("/tmp") / f"{state.self_id}_history.txt"

            # initialize a default fallback structure in case the file does not exist yet
            history_lines = []

            # check if a memory file from previous turns already exists on the disk
            if scratch.exists():
                try:
                    # json.loads() converts the raw text string read from the file back into a native Python dictionary
                    history_lines = scratch.read_text().splitlines()
                except Exception:
                    # if the file is corrupted or unreadable, silently ignore and keep the default structure
                    pass

            # safety check: ensure the data structure contains the expected "visited" list
            board_string = "".join([str(cell) if cell is not None else "." for row in state.board for cell in row])
            # append the current board state to the match history tracking
            history_lines.append(board_string)

            try:
                # json.dumps() converts the Python dictionary into a formatted JSON text string
                # write_text() then saves this string to the disk, replacing the file contents for the next turn
                scratch.write_text("\n".join(history_lines))
            except Exception:
                # if disk write fails (e.g., permissions or full directory), pass silently to avoid crashing the bot
                pass

            self.start_time = time.time()
            self.table = {}
            self.sync_bitboard(state)
            opponent_tokens = self.all_tokens ^ self.current_player_tokens
            mask = self.all_tokens

            # special case for the bot's first few turns
            if state.turn < 5:
                book_key = f"{self.all_tokens},{self.current_player_tokens}"
                if book_key in self.opening_book:
                    return self.opening_book[book_key]

            # Precalculate the single valid target bit_index for each column upfront
            lowest_rows = {}
            for col in state.legal_columns:
                for row in range(6):
                    bit_index = (col * 7) + row
                    if not (mask & (1 << bit_index)):
                        lowest_rows[col] = bit_index
                        break

            # check all columns for an instant win
            for column, bit_index in lowest_rows.items():
                if self.check_win(self.current_player_tokens | (1 << bit_index)):
                    return int(column)

            # check all columns for an instant loss if we don't block
            for column, bit_index in lowest_rows.items():
                if self.check_win(opponent_tokens | (1 << bit_index)):
                    return int(column)

            # build a list of columns where playing would not give the opponent a win next turn
            # so we can pass it to the Negamax search
            safe_legal_columns = []
            for column, bit_index in lowest_rows.items():
                row = bit_index % 7
                upper_bit_index = bit_index + 1
                if row < 5:
                    if self.check_win(opponent_tokens | (1 << upper_bit_index)):
                        continue
                safe_legal_columns.append(column)

            # when all hope is lost, extend the game and pray the opponent misses its winning play
            if not safe_legal_columns:
                safe_legal_columns = list(state.legal_columns)

            # search safe columns by priority order
            ordered_search_columns = [col for col in self.static_order if col in safe_legal_columns]

            # second part of this statement is a safety net in case ordered_search_columns ends up empty
            final_best_column = ordered_search_columns[0] if ordered_search_columns else state.legal_columns[len(state.legal_columns) // 2]
            current_depth = 1

            try:
                while True:
                    if time.time() - self.start_time > 0.88:
                        break

                    depth_best_score = float('-inf')
                    depth_best_column = final_best_column

                    # place the best guess from the previous depth at the front of the search
                    # and append the rest of the valid columns without modifying the original list
                    iteration_order = [final_best_column] + [col for col in ordered_search_columns if col != final_best_column]

                    # score all possible safe moves and retain the best result for next depth or final result
                    for column in iteration_order:
                        if time.time() - self.start_time > 0.88:
                            raise TimeoutError

                        bit_index = lowest_rows[column]
                        next_us = self.current_player_tokens | (1 << bit_index)
                        score = -self.alpha_beta(opponent_tokens, next_us, 1, current_depth, float('-inf'),
                                                 float('inf'))

                        if score > depth_best_score:
                            depth_best_score = score
                            depth_best_column = column

                    final_best_column = depth_best_column
                    current_depth += 1

            except TimeoutError:
                pass

            return int(final_best_column)

        except Exception:
            return state.legal_columns[len(state.legal_columns) // 2]