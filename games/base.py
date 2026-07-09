"""The contract every game module must implement.

The engine core (bot loader, sandboxing, tournament scheduler, replay
logging) never imports a specific game like Tron directly -- it only
talks to whatever object implements this interface. To add a new game
mode later (a maze race, a resource-collection game, a turn-based duel),
write a new module implementing `Game` and point run_tournament.py at it
with --game. Nothing else in the engine has to change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class Game(ABC):
    """One instance is created fresh per match -- never reused across
    matches, so there is no state leakage between them.
    """

    @abstractmethod
    def setup(self, bot_ids: List[str]) -> None:
        """Initialise the match for exactly these bot ids. Starting
        positions must be a fixed function of the bot count and order --
        never randomised -- so that running the same pairing twice with
        sides swapped is a fair way to cancel out first-move advantage.
        """

    @abstractmethod
    def view_for(self, bot_id: str) -> Any:
        """Return the read-only snapshot to hand to that bot's decide().
        Must not expose anything a bot shouldn't legitimately know."""

    @abstractmethod
    def step(self, moves: Dict[str, Any]) -> None:
        """Apply one turn's moves and advance internal state.

        `moves` maps bot_id -> whatever that bot's decide() returned, or
        None if it timed out, crashed, or returned something invalid --
        the game module decides what a forfeited turn means (in Tron,
        it means "keep going straight").
        """

    @abstractmethod
    def alive_bots(self) -> List[str]:
        """Bot ids still alive after the last step()."""

    @abstractmethod
    def is_over(self) -> bool:
        """True once the match has a result (win, loss, or draw)."""

    @abstractmethod
    def winners(self) -> List[str]:
        """Bot ids that won. Empty list means a draw. Only meaningful
        once is_over() is True."""

    @abstractmethod
    def frame(self) -> Dict[str, Any]:
        """A JSON-serialisable snapshot of the current turn, for the
        replay viewer. Called once after setup() and once after every
        step()."""

    @abstractmethod
    def serialize_view(self, view: Any) -> Dict[str, Any]:
        """Convert a view object (as returned by view_for) into a plain
        JSON-safe dict. Needed because each decide() call runs in its own
        subprocess (see engine/sandbox.py) -- the view has to cross that
        boundary as data, not as a live Python object."""

    @staticmethod
    @abstractmethod
    def deserialize_view(data: Dict[str, Any]) -> Any:
        """The inverse of serialize_view: reconstruct the view object
        inside the sandboxed subprocess before calling the bot's
        decide(). Must be a staticmethod -- it runs before any Game
        instance exists in that subprocess."""

    @staticmethod
    @abstractmethod
    def serialize_action(action: Any) -> Any:
        """Convert whatever decide() returned into a JSON-safe value,
        inside the sandboxed subprocess. Must be a staticmethod, for the
        same reason as deserialize_view -- no live Game instance exists
        in that subprocess. Most games just return a Move, in which case
        this is `action.name`; a turn-based game like Connect Four might
        return a plain column index instead, in which case this can be
        the identity function. Raise (any exception) for a value that
        isn't a legal action shape for this game -- the caller treats
        that identically to a crash: the turn is forfeited."""

    @staticmethod
    @abstractmethod
    def deserialize_action(data: Any) -> Any:
        """The inverse of serialize_action, run back in the main
        process before the action is fed to step()."""
