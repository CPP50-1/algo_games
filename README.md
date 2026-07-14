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
git clone <this repo>
cd tron-arena
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
  --workers 4 \           # matches to run in parallel (default: your CPU count)
  --finale                # also run one all-vs-all match at the end
```

## The games

| Game | Folder | Doc | Trains |
| --- | --- | --- | --- |
| Tron / light-cycles | `bots/` | [`docs/tron.md`](docs/tron.md) | graph traversal, BFS/DFS |
| Grid delivery / scheduling | `bots_delivery/` | [`docs/delivery.md`](docs/delivery.md) | priority queues, greedy-vs-optimal |
| Connect Four | `bots_connect4/` | [`docs/connect4.md`](docs/connect4.md) | minimax, memoization |
| Resource-constrained grid | `bots_resource/` | [`docs/resource.md`](docs/resource.md) | 0/1 knapsack, DP |
| Weighted terrain race | `bots_maze/` | [`docs/maze.md`](docs/maze.md) | Dijkstra/A* vs plain BFS |

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
  `MyBot()`, once per match (not once per turn -- see `engine/bot.py`'s
  docstring for what that means for `self.xyz` state and a common aliasing
  gotcha it introduces).
- Respond within the timeout (1.0s by default) on every individual turn. If
  you're too slow, raise an exception, or return something the game rejects,
  you forfeit that turn. What a forfeited turn means is up to the game (see
  that game's doc) -- but a timeout specifically also ends your bot's
  process for the rest of that match (every remaining turn becomes an
  automatic forfeit too), since a bot that hung once can't be trusted not to
  hang again. A single raised exception is less severe: it costs you only
  that one turn, and your state is intact again next turn.

See `CONTRIBUTING.md` for the full branch → pull request → CI → merge
workflow for submitting your bot.

## Architecture

The engine is deliberately split into two halves that never depend on each
other's internals:

```
engine/          -- reused forever, never changes per game
  bot.py               Bot base class + Move enum (the movement API most games use)
  loader.py            discovers bots/*.py (or bots_delivery/*.py, etc.) and
                        exposes load_bot_class_from_path, the single-file
                        loader every sandboxed runner below reuses
  persistent_sandbox.py launches one long-lived subprocess per bot for a
                        whole match, so a bot's own state survives between
                        turns -- see "How matches actually run" below
  bot_worker_loop.py    the long-lived script persistent_sandbox.py launches
  sandbox.py            the older one-shot "run a single decide() call and
                        exit" version, now only used by validate_ci.py's
                        quick smoke test
  bot_runner.py         the one-shot script sandbox.py launches
  game_loader.py        tiny helper: import a class from "module.path:ClassName"
  match.py              runs one match of any Game between 2+ bots
  tournament.py         round-robin / free-for-all scheduling, replay logging,
                        and running independent matches in parallel

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
a subprocess boundary as JSON. To add a new game mode, write a new module
implementing that interface and point `run_tournament.py` at it with
`--game module.path:ClassName`. Nothing in `engine/` has to change, and CI
picks up a new bots folder by adding one entry to the matrix in
`.github/workflows/validate_bot.yml`.

## How matches actually run, and why it's fast

Each bot in a match gets exactly one persistent subprocess for the whole
match (`engine/persistent_sandbox.py` + `engine/bot_worker_loop.py`), not a
fresh subprocess for every single move. The bot is instantiated once,
`decide()` is called on that same instance turn after turn, and its own
`self.xyz` state genuinely survives between turns -- see `engine/bot.py`'s
docstring for what that means in practice and a common gotcha it exposes.

This is also what makes the engine fast: launching a fresh Python
interpreter costs tens of milliseconds, and an earlier version of this
engine paid that cost on *every single move* (a one-shot `subprocess.run()`
per move, still available as `engine/sandbox.py` and used by the CI smoke
test, which only ever needs one call). Reusing one process per bot for the
whole match instead removes nearly all of that repeated cost -- a real
6-bot Tron round-robin (30 matches) dropped from about 132 seconds to about
14 seconds from this change alone, no parallelism involved.

On top of that, round-robin matches are independent of each other (each
gets its own fresh `Game` instance and its own bots), so `--workers N` runs
several matches at once across a process pool -- default is your CPU core
count, pass `--workers 1` to force fully sequential execution. On a
multi-core machine this compounds with the persistent-process speedup
above; on a single-core machine it won't help (there's nothing to actually
parallelize onto), but it also won't hurt, since a `--workers 1` code path
skips the process pool entirely.

A per-turn timeout on a long-lived process is trickier to enforce than on a
one-shot call (a blocking pipe read has no portable timeout of its own), so
`persistent_sandbox.py` uses a background thread reading into a queue and
enforces the timeout with a plain `queue.get(timeout=...)` -- this works
identically on Windows, macOS, and Linux, unlike `select()` on OS pipes,
which Windows doesn't support outside of sockets.

## Why every game here is deterministic

Games with any randomness (food spawns, shuffled decks, dice) produce
leaderboards that are partly noise -- you'd need to average over many matches
to see whose code is actually better. None of the five game modules above use
Python's `random` module anywhere: board layouts, job schedules, item
placements, and terrain maps are all fixed functions of the board size and a
few parameters, generated with deterministic scatter formulas instead. Given
the same board and the same bots, a match plays out identically every time.
The round-robin also plays every pairing twice with starting sides swapped
where that matters, cancelling out positional advantage so the leaderboard is
a clean measure of move quality, not draw luck.

This guarantee is about the *engine* -- a bot that itself calls Python's
`random` module without a fixed seed will still behave differently from run
to run no matter what the engine does, since that randomness is coming from
the bot's own code, not the board. That's a legitimate thing for a bot to
do, just worth knowing it trades away the "replays identically every time"
property for any match that bot is in.

## Safety notes for tournament day

A hung bot ends its own subprocess and every remaining turn that match
becomes an automatic forfeit for it -- it can never freeze the tournament or
affect another bot's match. A bot that raises an exception on a given turn
only forfeits that one turn; its process and state survive to try again next
turn. See `engine/persistent_sandbox.py` for the full reasoning behind
treating these two failure modes differently.

Process-per-bot sandboxing is implemented with `subprocess.Popen`/
`subprocess.run()` rather than Python's `multiprocessing` module
specifically so it behaves identically on Windows, macOS, and Linux --
`multiprocessing` needs to pickle the live bot object across the process
boundary, which breaks on Windows for bots loaded dynamically from an
arbitrary folder. Every sandboxed runner in this engine (one-shot and
persistent alike) instead reloads a bot fresh from its file path inside the
subprocess, and only ever passes plain JSON-safe data across a process
boundary -- never a live bot or game object.

This protects against accidents (hangs, crashes, runaway loops), not against a
deliberately malicious submission -- with a class of trainees you already
know, that's a low-stakes concern, but it's still good hygiene to run
tournament day from a disposable environment (fresh virtualenv, no sensitive
files nearby) rather than your primary machine.
