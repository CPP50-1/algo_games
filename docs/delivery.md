# Grid delivery / task scheduling

**Module:** `games/delivery.py`<br/>
**Bots folder:** `bots_delivery/`<br/>
**Trains:** priority queues (heapq), greedy-vs-optimal scheduling

## The game

Bots move around a shared grid picking up and delivering jobs before their
deadlines. Each job has a pickup cell, a dropoff cell, a value, and a
deadline (an absolute turn number). Landing on an available job's pickup
cell claims it automatically, each bot can carry at most one job at a
time. Landing on your carried job's dropoff cell on or before its deadline
delivers it and adds its value to your score. Miss the deadline, whether the
job is still unclaimed or you're carrying it, and it expires for zero value.

There are no walls and bots cannot die here, moving into the board edge is
simply a no-op, which doubles as a legal "wait in place" if that's ever the
right call.

The full job schedule is a fixed function of the board size and `num_jobs`,
generated with a golden-ratio scatter instead of Python's `random` module, so
the exact same match replays identically every time.

## Why it trains what it trains

Always heading for the *nearest* available job (naive greedy-by-distance)
regularly loses, because "close" and "urgent" are different things. A job
that looks cheap to reach but has no deadline pressure is often worth
skipping in favour of a farther job that's about to expire and pays more.
That's a scheduling problem, not a pathfinding problem, the natural tool is
a priority queue (`heapq`) ranked by something like slack time (deadline
minus turns needed to reach it), recomputed as jobs appear and expire, not a
single "distance to everything" scan repeated every turn.

## State your bot receives

`decide(state)` gets a `DeliveryView`:

```
self_id     - your bot id
width, height, turn
position    - your (x, y)
carrying    - the Job you're currently carrying, or None
score       - {bot_id: current score}
jobs        - every job that has appeared and not yet expired/been
               delivered, whether claimed or not
positions   - {bot_id: (x, y)} for every bot
```

A `Job` has: `id, pickup, dropoff, value, deadline, appear_turn, claimed_by`.

Return a `Move` (`UP`, `DOWN`, `LEFT`, `RIGHT`) from `engine.bot`.

## Reference bot

`bots_delivery/example_delivery_bot.py` - always walks toward the nearest
unclaimed job (or your own dropoff if already carrying something), ignoring
deadlines entirely. Beat it by weighing urgency alongside distance.

## Running it standalone

```bash
python3 run_tournament.py --game games.delivery:DeliveryGame \
  --bots-dir bots_delivery --out results_delivery \
  --game-kwargs '{"num_jobs": 12, "spawn_every": 6, "max_turns": 150}'
```

`--game-kwargs` accepts any of the `DeliveryGame` constructor's extra
parameters: `num_jobs` (how many jobs appear over the match), `spawn_every`
(turns between each job appearing), `max_turns` (match length).

## Contributing your bot

Add `bots_delivery/<your-first-name>.py` with one class subclassing `Bot`,
open a PR. See the top-level `CONTRIBUTING.md` for the full branch/PR/CI
workflow - it's the same process for every game module, only the target
folder changes.
