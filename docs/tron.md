# Tron - light-cycles

**Module:** `games/tron.py`<br/> 
**Bots folder:** `bots/`<br/>
**Trains:** graph traversal, BFS/DFS, flood-fill space reasoning

## The game

Every bot leaves a permanent wall behind it as it moves. You die by hitting
the board edge, any wall (yours or anyone else's), or another bot's head on
the same turn (a head-on collision kills both). Last bot alive wins; if
everyone dies on the same turn, it's a draw.

There is no food, no pickups, and no randomness anywhere in this module.
Starting positions are a fixed function of the board size and player count,
the only thing that decides a match is move quality.

## Why it trains what it trains

Naive movement (keep going, turn only when about to crash) loses quickly once
the board fills with trails. Doing well requires reasoning about how much
open space a given move leaves you - classic flood-fill / BFS territory
evaluation - rather than reacting one cell at a time.

## State your bot receives

`decide(state)` gets a `TronView`:

```
self_id     - your bot id
width       - board width
height      - board height
turn        - current turn number
positions   - {bot_id: (x, y)} for every bot still alive
alive       - list of bot ids still alive
walls        frozenset of every occupied (x, y) cell, anyone's trail
```

Return a `Move` (`UP`, `DOWN`, `LEFT`, `RIGHT`) from `engine.bot`. Coordinates:
`(0, 0)` is the top-left corner, x grows right, y grows down.

## Reference bot

`bots/example_bot.py` - keeps going straight, turns only when the next cell
would kill it, no lookahead at all. It's a legal baseline to test the engine
against, not a target. Beat it by reasoning about which move leaves you the
most reachable space, not just which move is immediately safe.

## Running it standalone

```bash
python3 run_tournament.py --bots-dir bots --out results
```

(This is also the default if you omit `--game` entirely.)

## Contributing your bot

Add `bots/<your-first-name>.py` with one class subclassing `Bot`, open a PR.
See the top-level `CONTRIBUTING.md` for the full branch/PR/CI workflow - it's
the same process for every game module, only the target folder changes.
