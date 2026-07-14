"""Runs one match of any Game between 2 or more bots.

Each bot gets exactly one persistent subprocess for the whole match
(see engine/persistent_sandbox.py) instead of a fresh subprocess per
single move. This is what lets ordinary self.xxx state on a bot survive
between turns, and it also removes the fixed interpreter-startup cost
that used to be paid on every single move -- a real speedup on top of
being what makes persistent bot memory possible at all.

This file only calls methods on the `Game` interface and the persistent
sandbox -- never anything game-specific -- so it works unchanged for
whatever game module gets loaded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.loader import LoadedBot
from engine.persistent_sandbox import PersistentBotProcess
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
    safety valve against a game module that never terminates; every
    shipped game module always terminates well before this on its own).
    Every bot's persistent subprocess is closed before returning, even
    if the match ends early or the loop raises.
    """
    game.setup(list(bots.keys()))
    game_cls_path = _game_cls_path(game)
    frames = [game.frame()]

    processes = {bot_id: PersistentBotProcess(bots[bot_id].path, game_cls_path) for bot_id in bots}
    try:
        while not game.is_over() and frames[-1]["turn"] < max_turns:
            moves = {
                bot_id: processes[bot_id].ask(game, game.view_for(bot_id), timeout)
                for bot_id in game.alive_bots()
            }
            game.step(moves)
            frames.append(game.frame())
    finally:
        for proc in processes.values():
            proc.close()

    return MatchResult(winners=game.winners(), turns=frames[-1]["turn"], frames=frames)
