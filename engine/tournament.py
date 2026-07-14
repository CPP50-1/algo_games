"""Tournament scheduling on top of engine.match.run_match.

`round_robin` runs every pair of bots twice, with sides swapped, so that
starting-corner / move-order advantage cancels out across the two
matches instead of leaking into the leaderboard. `free_for_all` pits
every bot against every other bot at once, for a tournament-day finale.

Matches within a round-robin are fully independent of each other (each
gets its own fresh Game instance and its own bots), so they run in
parallel across a process pool by default -- see `_play_one_match` for
why that worker reloads bots and the game class fresh from disk/import
rather than receiving live objects as arguments.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple, Type

from engine.game_loader import load_class
from engine.loader import LoadedBot, load_bot_class_from_path
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


def _play_one_match(spec: dict) -> dict:
    """Runs entirely inside a worker process (when parallel; the same
    function also runs directly in-process when max_workers == 1).

    Takes only plain, JSON-safe data as input -- bot ids and file paths
    as strings, the game class as a "module:ClassName" string, kwargs as
    a plain dict -- and reloads the game class and both bots fresh
    inside the worker, the same "reload from a path, never pickle a
    live object" pattern used everywhere else in this engine (see
    engine/sandbox.py's docstring). This is deliberate, not incidental:
    passing live Bot instances or dynamically-loaded classes as
    ProcessPoolExecutor arguments hits the exact same Windows pickling
    failure that the per-move sandbox was rewritten to avoid, since
    ProcessPoolExecutor uses the same pickling machinery multiprocessing
    does under the hood.

    Returns a small plain-data summary (never the full replay frames --
    those are written straight to disk by this worker instead of being
    pickled back to the main process, since they can be large and the
    main process only needs the outcome, not the play-by-play).
    """
    first, second = spec["first"], spec["second"]
    game_cls = load_class(spec["game_cls_path"])
    bot_a = LoadedBot(bot_id=first, path=spec["first_path"], instance=load_bot_class_from_path(spec["first_path"])())
    bot_b = LoadedBot(bot_id=second, path=spec["second_path"], instance=load_bot_class_from_path(spec["second_path"])())

    result = run_match(game_cls(**spec["game_kwargs"]), {first: bot_a, second: bot_b}, timeout=spec["timeout"])

    match_id = f"{first}_vs_{second}_{spec['swap_index']}"
    _save_replay(Path(spec["replay_dir"]) / f"{match_id}.json", [first, second], result)

    return {
        "match": match_id,
        "first": first,
        "second": second,
        "winners": result.winners,
        "is_draw": result.is_draw,
        "turns": result.turns,
    }


def round_robin(
    bots: Dict[str, LoadedBot],
    game_cls: Type[Game],
    game_kwargs: dict,
    timeout: float,
    replay_dir: str,
    max_workers: int = None,
) -> Tuple[List[dict], List[dict]]:
    """Returns (leaderboard, match_log).

    leaderboard: list of {bot, wins, losses, draws}, sorted best first.
    match_log:   list of {match, winners, turns} for every match played,
                 sorted by match id (execution order across a process
                 pool isn't deterministic, so this keeps the written
                 file's ordering stable and reproducible even though
                 wall-clock scheduling isn't).

    `max_workers` defaults to the number of CPUs available. Pass 1 to
    force fully sequential execution (useful for debugging, or on a
    machine where spinning up many processes at once is undesirable).
    """
    if max_workers is None:
        max_workers = os.cpu_count() or 1

    game_cls_path = f"{game_cls.__module__}:{game_cls.__qualname__}"
    specs = []
    for a, b in combinations(bots.keys(), 2):
        for swap_index, (first, second) in enumerate(((a, b), (b, a))):
            specs.append({
                "first": first, "second": second,
                "first_path": bots[first].path, "second_path": bots[second].path,
                "game_cls_path": game_cls_path, "game_kwargs": game_kwargs,
                "timeout": timeout, "swap_index": swap_index, "replay_dir": replay_dir,
            })

    standings = {bot_id: {"wins": 0, "losses": 0, "draws": 0} for bot_id in bots}
    match_log: List[dict] = []

    if max_workers <= 1:
        outcomes = [_play_one_match(spec) for spec in specs]
    else:
        outcomes = []
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_play_one_match, spec) for spec in specs]
            for future in as_completed(futures):
                outcomes.append(future.result())

    for outcome in outcomes:
        first, second = outcome["first"], outcome["second"]
        if outcome["is_draw"]:
            standings[first]["draws"] += 1
            standings[second]["draws"] += 1
        else:
            winner = outcome["winners"][0]
            loser = second if winner == first else first
            standings[winner]["wins"] += 1
            standings[loser]["losses"] += 1
        match_log.append({"match": outcome["match"], "winners": outcome["winners"], "turns": outcome["turns"]})

    match_log.sort(key=lambda m: m["match"])

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
    on-screen finale after the round-robin has already ranked everyone.
    Always sequential: there's only one match here, so there's nothing
    to parallelize.
    """
    result = run_match(game_cls(**game_kwargs), bots, timeout=timeout)
    _save_replay(Path(replay_path), list(bots.keys()), result)
    return result.winners
