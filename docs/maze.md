# Maze race with weighted terrain

**Module:** `games/maze.py`<br/>
**Bots folder:** `bots_maze/`<br/>
**Trains:** Dijkstra / A* over plain BFS

## The game

All bots race from the same start toward the same goal on a shared grid.
Every cell has a movement cost (1 = normal ground, higher = difficult
terrain); moving into a cost-N cell locks you out of moving again for N-1
extra turns, on top of the turn you just used. First bot to reach the goal
wins; if nobody gets there by `max_turns`, it's a draw.

The default map has a rectangular patch of expensive terrain sitting
directly on the straight line between start and goal. The terrain map is a
fixed function of the board size, so the exact same race replays
identically every time.

## Why it trains what it trains

A plain BFS treats every edge as cost 1, so it finds the path with the
*fewest cells*, which stops being the same thing as the path that takes
the *least time* the instant terrain costs vary. On the default map,
tunnelling straight through the expensive patch is fewer cells but slower in
total turns than detouring around it through cheap terrain, even though the
detour visits more cells. Concretely, on the default 21x15 map with a 5x
cost patch: straight through takes **48 turns**, detouring around takes
**26**, despite the detour covering more ground. Only a shortest-*path-by-
weight* algorithm (Dijkstra, or A* with an admissible heuristic like
Manhattan distance) reliably finds the detour; naive BFS/DFS on
cell-adjacency does not, because it has no concept of an edge costing more
than one hop.

## State your bot receives

`decide(state)` gets a `MazeView`:

```
self_id      - your bot id
width, height, turn
position     - your (x, y)
goal         - the shared target cell
busy_for     - turns remaining before you can move again (always 0 when
                decide() is actually being called on you)
terrain      - height x width grid of per-cell movement costs
positions    - {bot_id: (x, y)} for every bot still racing
```

Return a `Move` (`UP`, `DOWN`, `LEFT`, `RIGHT`) from `engine.bot`. You are
only ever asked for a move when you're free to act - `decide()` simply
won't be called while you're still "in transit" through expensive terrain,
so there's no need to track `busy_for` yourself unless you want to reason
about it for planning.

## Reference bot

`bots_maze/example_maze_bot.py` - plain breadth-first search over cell
adjacency, completely ignoring the `terrain` weights. It confidently walks
straight through the expensive patch because it "looks" shortest in cell
count. Beat it with a shortest-path-by-weight algorithm.

## Running it standalone

```bash
python3 run_tournament.py --game games.maze:MazeGame \
  --bots-dir bots_maze --out results_maze \
  --width 21 --height 15 --game-kwargs '{"band_cost": 5, "max_turns": 300}'
```

`--game-kwargs` accepts `band_cost` (how expensive the slow patch is) and
`max_turns` (draw threshold if nobody finishes).

## Contributing your bot

Add `bots_maze/<your-first-name>.py` with one class subclassing `Bot`, open
a PR. See the top-level `CONTRIBUTING.md` for the full branch/PR/CI
workflow - it's the same process for every game module, only the target
folder changes.
