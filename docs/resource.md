# Resource-constrained grid

**Module:** `games/resource.py`<br/>
**Bots folder:** `bots_resource/`<br/>
**Trains:** 0/1 knapsack, subset/DP reasoning

## The game

Each bot starts with its own fixed move budget and roams a shared grid
scattered with valued pickups. Moving costs one move from your budget;
landing on a pickup collects it automatically (first bot there takes it,
pickups are a shared, depletable resource). Once your budget hits zero
you're done moving for the rest of the match. Score is the sum of values
collected; highest score once every bot's budget has run out wins.

The pickup layout is a fixed function of the board size and `num_items`,
generated with the same golden-ratio scatter as the delivery game. Values
are deliberately uncorrelated with distance from anywhere, so "biggest
value" and "closest item" are different questions on purpose.

## Why it trains what it trains

Always walking to the *nearest* still-available pickup leaves value on the
table, because it never asks "given my remaining budget, which *combination*
of pickups reachable from here maximises total value?" That question, pick
a subset of items, each with a value and a cost, to maximise value under a
fixed budget, is 0/1 knapsack, and it rewards the same reasoning: a DP
table over (budget remaining) -> best achievable value, not a single greedy
scan repeated every turn.

The one honest twist versus textbook knapsack: an item's real "weight" is
the travel distance from wherever you happen to be, which changes as you
move and as other bots take items off the table. The DP has to be re-run (or
reasoned about approximately) as the game unfolds, not solved once up front.

## State your bot receives

`decide(state)` gets a `ResourceView`:

```
self_id       - your bot id
width, height, turn
position      - your (x, y)
moves_left    - your own remaining move budget
score         - {bot_id: current score}
items         - every pickup not yet collected: (id, position, value)
positions     - {bot_id: (x, y)} for every bot still able to move
```

Return a `Move` (`UP`, `DOWN`, `LEFT`, `RIGHT`) from `engine.bot`.

## Reference bot

`bots_resource/example_resource_bot.py` - always walks toward the nearest
available item, ignoring both its own remaining budget and every other
item's value. Beat it by reasoning about combinations of reachable items,
not single next steps.

## Running it standalone

```bash
python3 run_tournament.py --game games.resource:ResourceGame \
  --bots-dir bots_resource --out results_resource \
  --game-kwargs '{"num_items": 14, "move_budget": 40}'
```

`--game-kwargs` accepts `num_items` (how many pickups exist) and
`move_budget` (each bot's total moves for the match).

## Contributing your bot

Add `bots_resource/<your-first-name>.py` with one class subclassing `Bot`,
open a PR. See the top-level `CONTRIBUTING.md` for the full branch/PR/CI
workflow - it's the same process for every game module, only the target
folder changes.
