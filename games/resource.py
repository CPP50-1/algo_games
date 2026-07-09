"""Resource-constrained grid.

Each bot starts with its own fixed move budget and roams a shared grid
scattered with valued pickups. Moving costs one move from your budget;
landing on a pickup collects it automatically (first bot there takes
it -- pickups are a shared, depletable resource). Once your budget hits
zero you're done moving for the rest of the match, whether or not you
made it back anywhere. Score is simply the sum of values collected;
highest score when every bot's budget has run out wins.

The trap this is built to expose: always walking to the *nearest*
still-available pickup is a greedy strategy that regularly leaves value
on the table, because it never asks "given my remaining budget, which
*combination* of pickups reachable from here maximises total value?"
That question -- pick a subset of items, each with a value and an
effective cost, to maximise value under a fixed budget -- is exactly
the 0/1 knapsack problem, and it rewards the same reasoning: a DP table
over (budget remaining) -> best achievable value, rather than a single
greedy scan repeated every turn. The one twist versus textbook knapsack
is that an item's real "weight" is the travel distance from wherever
you happen to be, which changes as you move and as other bots take
items off the table -- so the DP has to be re-run (or reasoned about
approximately) as the game unfolds, not solved once up front.

Movement uses the same four-direction Move enum as every other game
module. There are no walls and bots cannot die here -- moving into the
board edge, or moving after your budget hits zero, is simply a no-op.

No randomness: the pickup layout is a fixed function of the board size
and --num-items, generated with the same golden-ratio scatter used by
the delivery game, so the exact same match replays identically every
time.

State handed to each bot's decide() is a `ResourceView`:
    self_id       -- your bot id
    width, height, turn
    position      -- your (x, y)
    moves_left    -- your own remaining move budget
    score         -- {bot_id: current score}
    items         -- every pickup not yet collected: (id, position, value)
    positions     -- {bot_id: (x, y)} for every bot still able to move
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from engine.bot import Move
from games.base import Game

Position = Tuple[int, int]

_GOLDEN_RATIO = 0.6180339887498949


@dataclass(frozen=True)
class Item:
    id: str
    position: Position
    value: int


@dataclass(frozen=True)
class ResourceView:
    self_id: str
    width: int
    height: int
    turn: int
    position: Position
    moves_left: int
    score: Dict[str, int]
    items: List[Item]
    positions: Dict[str, Position]


def _scatter_point(index: int, width: int, height: int) -> Position:
    fx = (index * _GOLDEN_RATIO) % 1.0
    fy = (index * _GOLDEN_RATIO * _GOLDEN_RATIO) % 1.0
    x = min(int(fx * width), width - 1)
    y = min(int(fy * height), height - 1)
    return (x, y)


def _generate_items(width: int, height: int, num_items: int) -> List[Item]:
    """Fixed, deterministic item layout. Values are deliberately not
    correlated with distance from the centre or from each other, so
    that "biggest value" and "closest item" are different questions --
    otherwise a naive greedy-by-value or greedy-by-distance strategy
    would accidentally be optimal and the exercise would prove nothing.
    """
    items = []
    for i in range(num_items):
        pos = _scatter_point(i, width, height)
        # A simple deterministic value spread: not monotonic in i and
        # not monotonic in distance from any fixed point, so no cheap
        # heuristic on the generator's structure gives the game away.
        value = 10 + ((i * 37) % 90)
        items.append(Item(id=f"item{i}", position=pos, value=value))
    return items


def _starting_positions(width: int, height: int, bot_ids: List[str]) -> Dict[str, Position]:
    n = len(bot_ids)
    positions = {}
    for i, bot_id in enumerate(bot_ids):
        x = round((i + 1) * width / (n + 1))
        x = min(max(x, 0), width - 1)
        positions[bot_id] = (x, height - 1)
    return positions


class ResourceGame(Game):
    def __init__(self, width: int = 20, height: int = 20, num_items: int = 14, move_budget: int = 40) -> None:
        self.width = width
        self.height = height
        self.num_items = num_items
        self.move_budget = move_budget

        self._turn = 0
        self._bot_ids: List[str] = []
        self._positions: Dict[str, Position] = {}
        self._moves_left: Dict[str, int] = {}
        self._score: Dict[str, int] = {}
        self._items_by_id: Dict[str, Item] = {}
        self._available_ids: List[str] = []

    def setup(self, bot_ids: List[str]) -> None:
        self._turn = 0
        self._bot_ids = list(bot_ids)
        self._positions = _starting_positions(self.width, self.height, self._bot_ids)
        self._moves_left = {b: self.move_budget for b in self._bot_ids}
        self._score = {b: 0 for b in self._bot_ids}
        items = _generate_items(self.width, self.height, self.num_items)
        self._items_by_id = {it.id: it for it in items}
        self._available_ids = [it.id for it in items]

    def view_for(self, bot_id: str) -> ResourceView:
        return ResourceView(
            self_id=bot_id,
            width=self.width,
            height=self.height,
            turn=self._turn,
            position=self._positions[bot_id],
            moves_left=self._moves_left[bot_id],
            score=dict(self._score),
            items=[self._items_by_id[i] for i in self._available_ids],
            positions=dict(self._positions),
        )

    def step(self, moves: Dict[str, Optional[Move]]) -> None:
        self._turn += 1

        for bot_id in self._bot_ids:
            if self._moves_left[bot_id] <= 0:
                continue
            move = moves.get(bot_id)
            if not isinstance(move, Move):
                continue  # forfeit -- no movement, but still counts as your turn passing
            self._moves_left[bot_id] -= 1
            x, y = self._positions[bot_id]
            nx, ny = x + move.dx, y + move.dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                self._positions[bot_id] = (nx, ny)

        # Collection: first bot (in id order, for determinism) standing
        # on an available item's cell takes it -- a shared, depletable
        # resource, same tie-break philosophy as the delivery game.
        for item_id in list(self._available_ids):
            item = self._items_by_id[item_id]
            claimants = sorted(b for b in self._bot_ids if self._positions[b] == item.position)
            if claimants:
                winner = claimants[0]
                self._score[winner] += item.value
                self._available_ids.remove(item_id)

    def alive_bots(self) -> List[str]:
        return [b for b in self._bot_ids if self._moves_left[b] > 0]

    def is_over(self) -> bool:
        return all(v <= 0 for v in self._moves_left.values())

    def winners(self) -> List[str]:
        if not self.is_over():
            return []
        best = max(self._score.values())
        return [b for b in self._bot_ids if self._score[b] == best]

    def frame(self) -> Dict:
        return {
            "turn": self._turn,
            "width": self.width,
            "height": self.height,
            "positions": {b: list(p) for b, p in self._positions.items()},
            "moves_left": dict(self._moves_left),
            "score": dict(self._score),
            "items": [
                {"id": it.id, "position": list(it.position), "value": it.value}
                for it in (self._items_by_id[i] for i in self._available_ids)
            ],
        }

    def serialize_view(self, view: ResourceView) -> Dict:
        return {
            "self_id": view.self_id,
            "width": view.width,
            "height": view.height,
            "turn": view.turn,
            "position": list(view.position),
            "moves_left": view.moves_left,
            "score": dict(view.score),
            "items": [{"id": it.id, "position": list(it.position), "value": it.value} for it in view.items],
            "positions": {b: list(p) for b, p in view.positions.items()},
        }

    @staticmethod
    def deserialize_view(data: Dict) -> ResourceView:
        return ResourceView(
            self_id=data["self_id"],
            width=data["width"],
            height=data["height"],
            turn=data["turn"],
            position=tuple(data["position"]),
            moves_left=data["moves_left"],
            score=dict(data["score"]),
            items=[Item(id=it["id"], position=tuple(it["position"]), value=it["value"]) for it in data["items"]],
            positions={b: tuple(p) for b, p in data["positions"].items()},
        )

    @staticmethod
    def serialize_action(action) -> str:
        return action.name

    @staticmethod
    def deserialize_action(data) -> Move:
        return Move[data]
