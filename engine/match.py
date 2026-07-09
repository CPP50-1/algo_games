"""Runs one match of any Game between 2 or more bots, with every single
move sandboxed. This file only calls methods on the `Game` interface
and the sandbox -- never anything Tron-specific -- so it works unchanged
for whatever game module gets loaded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.loader import LoadedBot
from engine.sandbox import call_with_timeout
from games.base import Game


def _game_cls_path(game: Game) -> str:
    cls = type(game)
    return f"{cls.__module__}:{cls.__qualname__}"


@dataclass
class MatchResult:
    winners: List[str]
    turns: int
    frames: List[dict] = field(default_factory=list)

    @property
    def is_draw(self) -> bool:
        return len(self.winners) != 1


def run_match(game: Game, bots: Dict[str, LoadedBot], timeout: float, max_turns: int = 2000) -> MatchResult:
    """`bots` maps bot_id -> LoadedBot. `game` must be freshly
    constructed -- setup() has not been called on it yet.

    Runs until the game reports it's over or `max_turns` is hit (a
    safety valve against a game module that never terminates; Tron
    always terminates on its own well before this).
    """
    game.setup(list(bots.keys()))
    game_cls_path = _game_cls_path(game)
    frames = [game.frame()]

    while not game.is_over() and frames[-1]["turn"] < max_turns:
        moves = {
            bot_id: call_with_timeout(
                game, game_cls_path, bots[bot_id].path, game.view_for(bot_id), timeout
            )
            for bot_id in game.alive_bots()
        }
        game.step(moves)
        frames.append(game.frame())

    return MatchResult(winners=game.winners(), turns=frames[-1]["turn"], frames=frames)
