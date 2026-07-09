# Bot arena engine

A minimal, dependency-free bot-battle engine built for training days: students
submit a Python file implementing one method, the engine runs everyone against
everyone, and produces a leaderboard plus watchable replays. No servers, no
Docker, no accounts -- one file per student, one command to run the whole
tournament.

This README covers the engine itself: how to run it, how it's put together,
and why it's built the way it is. Each game module has its own doc under
`docs/` with the rules, the state shape your bot receives, and how to submit
a bot for that specific game -- start there once you know which game you're
writing for.

## Quick start

Requires Python 3.12+. No third-party dependencies.

```bash
git clone <this-repo>
cd algo_games
python3 run_tournament.py --bots-dir bots --out results
```

This defaults to Tron. It loads every `.py` file in `bots/`, runs a full
round-robin (every pair of bots plays twice, with sides swapped), and writes:

- `results/leaderboard.json` -- wins / losses / draws per bot, sorted
- `results/match_log.json` -- one entry per match played
- `results/replays/*.json` -- one replay file per match

Open `viewer/replay_viewer.html` in a browser and load any file from
`results/replays/` to watch a match turn by turn -- it auto-detects which
game the replay is from and renders each one appropriately (Tron's walls,
delivery's pickup/dropoff markers, Connect Four's discs, resource pickups,
maze terrain heatmap).

To run a different game, point `--game` and `--bots-dir` at it:

```bash
python3 run_tournament.py --game games.delivery:DeliveryGame \
  --bots-dir bots_delivery --out results_delivery \
  --game-kwargs '{"num_jobs": 12, "spawn_every": 6, "max_turns": 150}'
```

Other useful flags (apply to any game):

```bash
python3 run_tournament.py --bots-dir bots --out results \
  --timeout 1.0 \        # seconds allowed per decide() call
  --width 21 --height 21 \
  --finale                # also run one all-vs-all match at the end
```

## The games

| Game                       | Folder           | Doc                                    | Trains                             |
|----------------------------|------------------|----------------------------------------|------------------------------------|
| Tron / light-cycles        | `bots/`          | [`docs/tron.md`](docs/tron.md)         | graph traversal, BFS/DFS           |
| Grid delivery / scheduling | `bots_delivery/` | [`docs/delivery.md`](docs/delivery.md) | priority queues, greedy-vs-optimal |
| Connect Four               | `bots_connect4/` | [`docs/connect4.md`](docs/connect4.md) | minimax, memoization               |
| Resource-constrained grid  | `bots_resource/` | [`docs/resource.md`](docs/resource.md) | 0/1 knapsack, DP                   |
| Weighted terrain race      | `bots_maze/`     | [`docs/maze.md`](docs/maze.md)         | Dijkstra/A* vs plain BFS           |

One line each:

- **Tron** -- last bot alive wins; everyone leaves a permanent wall behind them.
- **Delivery** -- pick up and deliver jobs before their deadlines expire.
- **Connect Four** -- classic turn-based 4-in-a-row, adversarial with perfect information.
- **Resource grid** -- limited move budget, scattered pickups, maximise value collected.
- **Weighted terrain race** -- first to the goal wins, but no single fixed detour is optimal once terrain costs vary.

## Writing a bot

One file, one class, subclassing `Bot` from `engine/bot.py` -- this part is
identical no matter which game module is loaded:

```python
from engine.bot import Bot, Move

class MyBot(Bot):
    def decide(self, state):
        # the shape of `state`, and what decide() should return, depends
        # on the game -- see that game's doc under docs/
        return Move.UP
```

Rules your bot must follow, for any game:

- Exactly one `Bot` subclass per file. Zero or several and the file is
  skipped with a warning, not loaded.
- No required constructor arguments -- the engine instantiates your bot with
  `MyBot()`.
- Respond within the timeout (1.0s by default). If you're too slow, raise an
  exception, or return something the game rejects, you forfeit the turn.
  What a forfeited turn means is up to the game (see that game's doc).

See `CONTRIBUTING.md` for the full branch → pull request → CI → merge
workflow for submitting your bot.

## Architecture

The engine is deliberately split into two halves that never depend on each
other's internals:

```
engine/          -- reused forever, never changes per game
  bot.py           Bot base class + Move enum (the movement API most games use)
  loader.py        discovers and imports bots/*.py (or bots_delivery/*.py, etc.)
  sandbox.py       runs one decide() call in its own subprocess with a timeout
  bot_runner.py    the standalone script that subprocess actually launches
  game_loader.py   tiny helper: import a class from "module.path:ClassName"
  match.py         runs one match of any Game between 2+ bots
  tournament.py    round-robin / free-for-all scheduling, replay logging

games/           -- swappable, one module per game type
  base.py          the Game interface every game module implements
  tron.py, delivery.py, connect4.py, resource.py, maze.py

bots/, bots_delivery/, bots_connect4/, bots_resource/, bots_maze/
                 -- one file per student, one folder per game
viewer/          -- replay_viewer.html, opens a replay JSON and animates it
docs/            -- one .md per game module: rules, state shape, how to contribute
```

`engine/match.py` never imports any specific game module -- it only calls
methods defined on the abstract `Game` interface in `games/base.py`:
`setup`, `view_for`, `step`, `alive_bots`, `is_over`, `winners`, `frame`, and
a pair of `serialize_view`/`deserialize_view` plus `serialize_action`/
`deserialize_action` methods that let a view or an action of *any* shape
(not just the `Move` enum -- Connect Four uses plain column integers) cross
the sandbox's subprocess boundary as JSON. To add a new game mode, write a
new module implementing that interface and point `run_tournament.py` at it
with `--game module.path:ClassName`. Nothing in `engine/` has to change, and
CI picks up a new bots folder by adding one entry to the matrix in
`.github/workflows/validate_bot.yml`.
