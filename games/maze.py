"""Weighted terrain race.

All bots race from the same start toward the same goal on a shared
grid. Every cell has a movement cost (1 = normal ground, higher =
difficult terrain like mud or a swamp); moving into a cost-N cell locks
you out of moving again for N-1 extra turns, on top of the turn you
just used. First bot to reach the goal wins; if nobody gets there by
--max-turns, it's a draw.

There are no walls anywhere -- every cell is walkable, just some cost
more time than others. (This module used to be called "maze race",
which was misleading: a maze implies cells you physically cannot enter,
and this game has none. "Weighted terrain" is the honest name.)

The trap this is built to expose: a plain BFS treats every edge as
cost 1, so it finds the path with the *fewest cells* -- which is not
the same thing as the path that takes the *least time* the instant
terrain costs vary. The default map has two offset cost-bands, each
open only on one side (one has a gap near the top, the other a gap
near the bottom), positioned so a single straight-line detour in either
direction avoids one band but walks straight through the other. There
is no single fixed rule ("always go up", "always go down") that's
optimal -- the only way to do well is to actually route through both
gaps, which means evaluating the whole board's costs, not reacting to
whichever costly cell happens to be immediately ahead. Concretely, on
the default 21x15 map: going straight through both bands costs 52
turns, a naive "always detour up" and a naive "always detour down" both
cost 50 (tied -- neither fixed direction is actually better), and the
properly planned route through both gaps costs 40. Only a shortest-
*path-by-weight* algorithm (Dijkstra, or A* with an admissible
heuristic like Manhattan distance ignoring terrain) reliably finds that
route; naive BFS/DFS on cell-adjacency does not, because it has no
concept of an edge costing more than one hop, and a shallow "avoid
whatever's in front of me" heuristic does not either, because it never
looks far enough ahead to see the second band coming.

Turn handling: like the delivery and resource games, all bots that are
currently free to act are queried simultaneously each turn -- but a bot
that just entered expensive terrain is excluded from `alive_bots()` for
the next few turns while it's still "in transit" (an implementation
detail exposed to bots as `busy_for` in the view, mostly so a replay
viewer or curious bot can display/reason about it; you cannot act while
busy_for > 0, decide() simply won't be called on you until it's 0). This
means expensive terrain isn't a stat you multiply into your own
distance formula -- it's the engine itself refusing to ask a bot for
its next move until its previous, costlier move has finished playing
out. Moving into the board edge is a no-op, same as every other game
module.

No randomness: the terrain map is a fixed function of the board size,
so the exact same race replays identically every time.

State handed to each bot's decide() is a `MazeView`:
    self_id      -- your bot id
    width, height, turn
    position     -- your (x, y)
    goal         -- the shared target cell
    busy_for     -- turns remaining before you can move again (always 0
                     when decide() is actually called on you)
    terrain      -- height x width grid of per-cell movement costs
    positions    -- {bot_id: (x, y)} for every bot still racing
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from engine.bot import Move
from games.base import Game

Position = Tuple[int, int]
Terrain = Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class MazeView:
    self_id: str
    width: int
    height: int
    turn: int
    position: Position
    goal: Position
    busy_for: int
    terrain: Terrain
    positions: Dict[str, Position]


def _generate_terrain(width: int, height: int, band_cost: int) -> List[List[int]]:
    """Fixed, deterministic terrain: two offset cost-bands, each a gap
    on only one side, so no single detour direction avoids both.

    Band A sits roughly in the left-middle third of the board and is
    open only near the top (a bot has to be above a certain row to
    cross its columns cheaply). Band B sits roughly in the right-middle
    third and is open only near the bottom (the opposite side). A bot
    that detours up avoids A but walks straight through B; a bot that
    detours down avoids B but walks straight through A. Only a route
    that goes up for A's columns and back down for B's columns avoids
    both -- see the module docstring for the actual turn counts this
    produces on the default board size.
    """
    a_x0, a_x1 = round(width * 5 / 21), round(width * 9 / 21)
    b_x0, b_x1 = round(width * 12 / 21), round(width * 16 / 21)
    a_gap_row = round(height * 3 / 15)   # band A costs apply at row >= this
    b_gap_row = round(height * 10 / 15)  # band B costs apply at row < this

    terrain = [[1] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            in_band_a = a_x0 <= x < a_x1 and y >= a_gap_row
            in_band_b = b_x0 <= x < b_x1 and y < b_gap_row
            if in_band_a or in_band_b:
                terrain[y][x] = band_cost
    return terrain


class MazeGame(Game):
    def __init__(self, width: int = 21, height: int = 15, band_cost: int = 5, max_turns: int = 300) -> None:
        self.width = width
        self.height = height
        self.band_cost = band_cost
        self.max_turns = max_turns

        self._terrain: List[List[int]] = []
        self._start: Position = (0, height // 2)
        self._goal: Position = (width - 1, height // 2)
        self._turn = 0
        self._bot_ids: List[str] = []
        self._positions: Dict[str, Position] = {}
        self._free_at: Dict[str, int] = {}  # turn number each bot becomes free to move again
        self._finish_order: List[str] = []

    def setup(self, bot_ids: List[str]) -> None:
        self._terrain = _generate_terrain(self.width, self.height, self.band_cost)
        self._start = (0, self.height // 2)
        self._goal = (self.width - 1, self.height // 2)
        self._turn = 0
        self._bot_ids = list(bot_ids)
        self._positions = {b: self._start for b in self._bot_ids}
        self._free_at = {b: 0 for b in self._bot_ids}
        self._finish_order = []

    def view_for(self, bot_id: str) -> MazeView:
        return MazeView(
            self_id=bot_id,
            width=self.width,
            height=self.height,
            turn=self._turn,
            position=self._positions[bot_id],
            goal=self._goal,
            busy_for=max(0, self._free_at[bot_id] - self._turn),
            terrain=tuple(tuple(row) for row in self._terrain),
            positions=dict(self._positions),
        )

    def step(self, moves: Dict[str, Optional[Move]]) -> None:
        self._turn += 1

        for bot_id in sorted(moves.keys()):
            move = moves.get(bot_id)
            if not isinstance(move, Move):
                continue  # forfeit -- stays put, wastes this turn

            x, y = self._positions[bot_id]
            nx, ny = x + move.dx, y + move.dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue  # walked into the edge -- no-op, free to try again next turn

            cost = self._terrain[ny][nx]
            self._positions[bot_id] = (nx, ny)
            self._free_at[bot_id] = self._turn + (cost - 1)

            if (nx, ny) == self._goal and bot_id not in self._finish_order:
                self._finish_order.append(bot_id)

    def alive_bots(self) -> List[str]:
        if self.is_over():
            return []
        return [b for b in self._bot_ids if self._turn >= self._free_at[b]]

    def is_over(self) -> bool:
        return bool(self._finish_order) or self._turn >= self.max_turns

    def winners(self) -> List[str]:
        return self._finish_order if self._finish_order else []

    def frame(self) -> Dict:
        return {
            "turn": self._turn,
            "width": self.width,
            "height": self.height,
            "goal": list(self._goal),
            "positions": {b: list(p) for b, p in self._positions.items()},
            "busy_for": {b: max(0, self._free_at[b] - self._turn) for b in self._bot_ids},
            "finished": list(self._finish_order),
            "terrain": [list(row) for row in self._terrain] if self._turn == 0 else None,
        }

    def serialize_view(self, view: MazeView) -> Dict:
        return {
            "self_id": view.self_id,
            "width": view.width,
            "height": view.height,
            "turn": view.turn,
            "position": list(view.position),
            "goal": list(view.goal),
            "busy_for": view.busy_for,
            "terrain": [list(row) for row in view.terrain],
            "positions": {b: list(p) for b, p in view.positions.items()},
        }

    @staticmethod
    def deserialize_view(data: Dict) -> MazeView:
        return MazeView(
            self_id=data["self_id"],
            width=data["width"],
            height=data["height"],
            turn=data["turn"],
            position=tuple(data["position"]),
            goal=tuple(data["goal"]),
            busy_for=data["busy_for"],
            terrain=tuple(tuple(row) for row in data["terrain"]),
            positions={b: tuple(p) for b, p in data["positions"].items()},
        )

    @staticmethod
    def serialize_action(action) -> str:
        return action.name

    @staticmethod
    def deserialize_action(data) -> Move:
        return Move[data]