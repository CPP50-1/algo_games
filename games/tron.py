"""Tron / light-cycles.

Every bot leaves a permanent wall behind it as it moves. You die by
hitting the board edge, any wall (yours or anyone else's), or another
bot's head this turn (a head-on collision kills both). Last bot alive
wins; if everyone dies on the same turn, it's a draw.

There is no food, no pickups, and no randomness anywhere in this module.
Starting positions are a fixed function of the board size and player
count (see `_starting_layout` below) -- the only thing that decides a
match is move quality, which is the entire point.

State handed to each bot's decide() is a `TronView`:
    self_id     -- your bot id (str)
    width       -- board width
    height      -- board height
    turn        -- current turn number
    positions   -- {bot_id: (x, y)} for every bot still alive
    alive       -- list of bot ids still alive
    walls       -- frozenset of every occupied (x, y) cell, anyone's trail

Coordinates: (0, 0) is the top-left corner, x grows right, y grows down.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from engine.bot import Move
from games.base import Game

Position = Tuple[int, int]


@dataclass(frozen=True)
class TronView:
    self_id: str
    width: int
    height: int
    turn: int
    positions: Dict[str, Position]
    alive: List[str]
    walls: FrozenSet[Position]


def _starting_layout(width: int, height: int, n: int) -> List[Tuple[Position, Move]]:
    """Fixed starting (position, facing) pairs for n bots. No randomness."""
    if n == 2:
        mid = height // 2
        return [((2, mid), Move.RIGHT), ((width - 3, mid), Move.LEFT)]

    # 3+ players: spread evenly around a circle, facing the centre.
    cx, cy = (width - 1) / 2, (height - 1) / 2
    radius = min(width, height) / 2 - 2
    layout: List[Tuple[Position, Move]] = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        x = min(max(round(cx + radius * math.cos(angle)), 1), width - 2)
        y = min(max(round(cy + radius * math.sin(angle)), 1), height - 2)
        dx, dy = cx - x, cy - y
        if abs(dx) >= abs(dy):
            facing = Move.RIGHT if dx > 0 else Move.LEFT
        else:
            facing = Move.DOWN if dy > 0 else Move.UP
        layout.append(((x, y), facing))
    return layout


class TronGame(Game):
    def __init__(self, width: int = 21, height: int = 21) -> None:
        self.width = width
        self.height = height
        self._turn = 0
        self._alive: List[str] = []
        self._positions: Dict[str, Position] = {}
        self._facing: Dict[str, Move] = {}
        self._walls: set = set()
        self._died_this_turn: List[str] = []

    def setup(self, bot_ids: List[str]) -> None:
        layout = _starting_layout(self.width, self.height, len(bot_ids))
        self._positions = {}
        self._facing = {}
        self._walls = set()
        for bot_id, (pos, facing) in zip(bot_ids, layout):
            self._positions[bot_id] = pos
            self._facing[bot_id] = facing
            self._walls.add(pos)
        self._alive = list(bot_ids)
        self._turn = 0
        self._died_this_turn = []

    def view_for(self, bot_id: str) -> TronView:
        return TronView(
            self_id=bot_id,
            width=self.width,
            height=self.height,
            turn=self._turn,
            positions=dict(self._positions),
            alive=list(self._alive),
            walls=frozenset(self._walls),
        )

    def step(self, moves: Dict[str, Optional[Move]]) -> None:
        self._turn += 1
        proposed: Dict[str, Position] = {}

        for bot_id in self._alive:
            move = moves.get(bot_id)
            if not isinstance(move, Move):
                move = self._facing[bot_id]  # forfeit -> keep going straight
            self._facing[bot_id] = move
            x, y = self._positions[bot_id]
            proposed[bot_id] = (x + move.dx, y + move.dy)

        dead = set()
        for bot_id, pos in proposed.items():
            x, y = pos
            if not (0 <= x < self.width and 0 <= y < self.height):
                dead.add(bot_id)
            elif pos in self._walls:
                dead.add(bot_id)

        # Head-on collision: two or more survivors proposing the same cell.
        counts = Counter(proposed.values())
        for bot_id, pos in proposed.items():
            if counts[pos] > 1:
                dead.add(bot_id)

        self._died_this_turn = [b for b in self._alive if b in dead]

        # Record every proposed position (including fatal ones) so the
        # replay can show exactly where a crash happened.
        for bot_id, pos in proposed.items():
            self._positions[bot_id] = pos

        still_alive = [b for b in self._alive if b not in dead]
        for bot_id in still_alive:
            self._walls.add(proposed[bot_id])
        self._alive = still_alive

    def alive_bots(self) -> List[str]:
        return list(self._alive)

    def is_over(self) -> bool:
        return len(self._alive) <= 1

    def winners(self) -> List[str]:
        return list(self._alive) if len(self._alive) == 1 else []

    def frame(self) -> Dict:
        return {
            "turn": self._turn,
            "width": self.width,
            "height": self.height,
            "positions": {b: list(p) for b, p in self._positions.items()},
            "alive": list(self._alive),
            "died": list(self._died_this_turn),
            "walls": [list(p) for p in sorted(self._walls)],
        }

    def serialize_view(self, view: TronView) -> Dict:
        return {
            "self_id": view.self_id,
            "width": view.width,
            "height": view.height,
            "turn": view.turn,
            "positions": {b: list(p) for b, p in view.positions.items()},
            "alive": list(view.alive),
            "walls": [list(w) for w in view.walls],
        }

    @staticmethod
    def deserialize_view(data: Dict) -> TronView:
        return TronView(
            self_id=data["self_id"],
            width=data["width"],
            height=data["height"],
            turn=data["turn"],
            positions={b: tuple(p) for b, p in data["positions"].items()},
            alive=list(data["alive"]),
            walls=frozenset(tuple(w) for w in data["walls"]),
        )

    @staticmethod
    def serialize_action(action) -> str:
        return action.name  # raises AttributeError for anything that isn't a Move -- treated as forfeit

    @staticmethod
    def deserialize_action(data) -> Move:
        return Move[data]
