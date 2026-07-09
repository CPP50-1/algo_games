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
        setting; 0.2s by default). If you take too long, raise an
        exception, or return something that isn't a `Move`, you forfeit
        the turn -- in Tron that means you keep going straight, which
        is usually fatal. There is no partial credit for "almost".
        """
        raise NotImplementedError
