# Connect Four

**Module:** `games/connect4.py`<br/> 
**Bots folder:** `bots_connect4/`<br/>
**Trains:** minimax / game-tree search, memoization

## The game

Two bots alternate dropping a piece into a column; pieces fall to the lowest
empty row in that column. First to connect four in a row -- horizontally,
vertically, or diagonally -- wins. Board full with no winner is a draw.

This is a different shape of game from the others in this repo: it's
**turn-based**, not simultaneous, and it's adversarial with perfect
information and zero randomness. `alive_bots()` returns a single-element
list - whichever bot is "to move" - so the engine only spends a sandboxed
subprocess call on the player whose move actually matters that turn.

Actions here are plain **column indices** (an `int`, 0-based, left to
right), not the `Move` enum used by the other games -- `decide()` should
`return` an integer.

## Why it trains what it trains

The entire game state is a small grid with three possible values per cell,
small enough to search several moves deep inside the timeout, which is
exactly the point. A bot that only checks "can I win this move / can I block
an immediate threat" (a shallow, one-ply heuristic) will regularly lose to a
bot that actually searches the game tree, minimax, ideally with alpha-beta
pruning and a transposition table (memoization) so the same board position
reached via a different move order isn't re-explored from scratch.

## State your bot receives

`decide(state)` gets a `ConnectFourView`:

```
self_id       -- your bot id
opponent_id   -- the other bot id
width, height -- board dimensions (7x6 by default)
board         -- height x width grid, row 0 is the TOP row; each cell is
                 your bot id, the opponent's bot id, or None
legal_columns -- columns that aren't full yet, in order
turn          -- turn number (also how many pieces are on the board)
```

Return an `int` column index. An illegal or missing move (timeout, crash,
non-integer return) falls back to the leftmost legal column rather than
ending the match -- one bad turn shouldn't be an instant loss, but it will
usually put you in a worse position, so it's still worth avoiding.

## Reference bot

`bots_connect4/example_connect4_bot.py` -- plays a winning move if one exists
right now, otherwise blocks the opponent's immediate winning move, otherwise
plays leftmost. No real lookahead. Beat it with actual search depth.

## Running it standalone

```bash
python run_tournament.py --game games.connect4:ConnectFourGame --bots-dir bots_connect4 --out results_connect4 --width 7 --height 6
```

Connect Four is strictly 2-player - a round-robin with more than two loaded
bots will still work (every pair plays each other), it just isn't a
free-for-all like the other games.

## Contributing your bot

Add `bots_connect4/<your-first-name>.py` with one class subclassing `Bot`,
open a PR. See the top-level `CONTRIBUTING.md` for the full branch/PR/CI
workflow - it's the same process for every game module, only the target
folder changes.
