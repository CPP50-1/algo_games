"""Tournament scheduling on top of engine.match.run_match.

`round_robin` runs every pair of bots twice, with sides swapped, so that
starting-corner / move-order advantage cancels out across the two
matches instead of leaking into the leaderboard. `free_for_all` pits
every bot against every other bot at once, for a tournament-day finale.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple, Type

from engine.loader import LoadedBot
from engine.match import run_match
from games.base import Game


def _save_replay(path: Path, players: List[str], result) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8" explicitly -- Windows' default open() encoding is
    # locale-dependent (often cp1252 on a French system), which can
    # raise on non-ASCII bot ids/names rather than writing them cleanly.
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"players": players, "winners": result.winners, "turns": result.turns, "frames": result.frames},
            f,
        )


def round_robin(
    bots: Dict[str, LoadedBot],
    game_cls: Type[Game],
    game_kwargs: dict,
    timeout: float,
    replay_dir: str,
) -> Tuple[List[dict], List[dict]]:
    """Returns (leaderboard, match_log).

    leaderboard: list of {bot, wins, losses, draws}, sorted best first.
    match_log:   list of {match, winners, turns} for every match played.
    """
    standings = {bot_id: {"wins": 0, "losses": 0, "draws": 0} for bot_id in bots}
    match_log: List[dict] = []

    for a, b in combinations(bots.keys(), 2):
        for swap_index, (first, second) in enumerate(((a, b), (b, a))):
            pair = {first: bots[first], second: bots[second]}
            result = run_match(game_cls(**game_kwargs), pair, timeout=timeout)

            if result.is_draw:
                standings[first]["draws"] += 1
                standings[second]["draws"] += 1
            else:
                winner = result.winners[0]
                loser = second if winner == first else first
                standings[winner]["wins"] += 1
                standings[loser]["losses"] += 1

            match_id = f"{first}_vs_{second}_{swap_index}"
            _save_replay(Path(replay_dir) / f"{match_id}.json", [first, second], result)
            match_log.append({"match": match_id, "winners": result.winners, "turns": result.turns})

    leaderboard = [
        {"bot": bot_id, **stats}
        for bot_id, stats in sorted(
            standings.items(),
            key=lambda kv: (kv[1]["wins"], -kv[1]["losses"], kv[1]["draws"]),
            reverse=True,
        )
    ]
    return leaderboard, match_log


def free_for_all(
    bots: Dict[str, LoadedBot],
    game_cls: Type[Game],
    game_kwargs: dict,
    timeout: float,
    replay_path: str,
) -> List[str]:
    """Runs every loaded bot in a single match. Returns the winner list
    (empty if a draw) and writes one replay file -- good for a live,
    on-screen finale after the round-robin has already ranked everyone."""
    result = run_match(game_cls(**game_kwargs), bots, timeout=timeout)
    _save_replay(Path(replay_path), list(bots.keys()), result)
    return result.winners
