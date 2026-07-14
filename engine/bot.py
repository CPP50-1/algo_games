"""Base class and move enum that every student bot is written against.

This file never changes between game modules. Whatever game is loaded
that week, your bot still subclasses `Bot` and returns a `Move` from
`decide()`. Only the *shape of the state* you receive changes per game.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class Move(Enum):
    """The four legal moves. Diagonal movement does not exist."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]


class Bot(ABC):
    """Subclass this once per file. Exactly one `Bot` subclass per file --
    the engine will refuse to load a file with zero or several.

    Your bot is instantiated exactly ONCE per match, not once per turn --
    __init__ runs at the start of the match, and the same instance
    answers every decide() call for the rest of it. This means ordinary
    `self.xyz = ...` attributes genuinely persist between turns, the
    same way they would in any normal long-running Python program: you
    can build up a plan across turns, remember what you've already seen,
    cache an expensive computation, count things, and so on.

    The one gotcha worth knowing up front: persistence means *aliasing*
    bugs are now real bugs, not accidents that happen to reset
    themselves every turn. If you do this:

        self._directions = [Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT]
        ...
        def decide(self, state):
            options = self._directions      # NOT a copy -- same list object
            options.remove(some_move)       # this mutates self._directions too!

    `self._directions` will have one less element every time decide()
    removes something from `options`, forever, for the rest of the
    match -- because `options` and `self._directions` are the same list
    in memory. Write `options = list(self._directions)` (or
    `self._directions.copy()`) if you want a fresh copy to mutate each
    turn without touching the original.

    Do not override `__init__` with required arguments: the engine
    instantiates your bot with no arguments at all.
    """

    #: Shown on the leaderboard. Defaults to your class name if you don't
    #: set it yourself.
    name: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = type(self).__name__

    @abstractmethod
    def decide(self, state: Any) -> Move:
        """Return the move to make this turn.

        `state` is a read-only snapshot handed to you fresh every turn --
        mutating it does nothing and is never seen by the engine or any
        other bot. Its exact shape depends on which game module is
        loaded (see that module's docstring, e.g. games/tron.py).

        You are on a strict time budget (the tournament's --timeout
        setting; 1.0s by default) for THIS turn specifically. If you
        take too long on any single turn, raise an exception, or return
        something that isn't a `Move`, you forfeit that turn -- in Tron
        that means you keep going straight, which is usually fatal.
        There is no partial credit for "almost". A timeout is treated
        more seriously than a raised exception, though: timing out kills
        your bot's process outright and every remaining turn this match
        is an automatic forfeit too, since a bot that hung once can't be
        trusted not to hang again -- whereas a single caught exception
        only costs you that one turn, and you get to try again next
        turn with your state intact.
        """
        raise NotImplementedError
