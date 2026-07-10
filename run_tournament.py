#!/usr/bin/env python3
"""Command-line entry point for tournament day.

Basic usage (Tron, the default game):
    python run_tournament.py --bots-dir bots --out results

Pointing it at a different game module, on macOS/Linux (bash/zsh):
    python run_tournament.py --game games.delivery:DeliveryGame \
        --bots-dir bots_delivery --out results_delivery \
        --game-kwargs '{"num_jobs": 12, "spawn_every": 6, "max_turns": 150}'

On Windows, quoting a JSON string with embedded double quotes is
awkward in both cmd.exe and PowerShell (this is a Windows shell
limitation, not a Python one). The reliable fix is to put the JSON in
a file instead and pass it with an "@" prefix:
    python run_tournament.py --game games.delivery:DeliveryGame ^
        --bots-dir bots_delivery --out results_delivery ^
        --game-kwargs @delivery_kwargs.json
where delivery_kwargs.json just contains:
    {"num_jobs": 12, "spawn_every": 6, "max_turns": 150}
This "@file" form works identically on every OS, so it's the safest
default to reach for even outside Windows.

Loads every bot in --bots-dir, runs a full round-robin (each pair of
bots plays twice, sides swapped), writes a leaderboard and one replay
JSON per match into --out, and prints the final standings.

Add --finale to also run a single all-vs-all free-for-all after the
round-robin, for a live finale you can project on screen. (For a
non-adversarial game like delivery, "free-for-all" just means everyone
plays the same schedule at once and the leaderboard is by score, not
survival -- still a fine finale to watch.)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.loader import load_bots
from engine.tournament import free_for_all, round_robin
from engine.game_loader import load_class


def _load_game_kwargs(value: str) -> dict:
    """Accepts either a literal JSON string, or "@path/to/file.json" to
    read the JSON from a file instead -- the latter sidesteps shell
    quoting entirely, which is unreliable for JSON containing double
    quotes on Windows in particular.
    """
    if value.startswith("@"):
        path = Path(value[1:])
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"--game-kwargs: could not read {path}: {exc}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--game-kwargs: {path} is not valid JSON: {exc}")

    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "--game-kwargs: could not parse as JSON "
            f"({exc}). Got: {value!r}\n"
            "If you're on Windows and this looks mangled (e.g. missing "
            "quotes), put the JSON in a file and pass --game-kwargs "
            "@yourfile.json instead -- see the top of this script's "
            "--help output for an example."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bots-dir", default="bots", help="folder containing one .py file per bot")
    parser.add_argument("--out", default="results", help="folder to write leaderboard + replays into")
    parser.add_argument(
        "--game", default="games.tron:TronGame",
        help="which game module to run, as 'module.path:ClassName' (default: games.tron:TronGame)",
    )
    parser.add_argument(
        "--game-kwargs", default="{}",
        help="JSON object of extra keyword arguments for the game's constructor, "
             "e.g. '{\"num_jobs\": 12}' for games.delivery:DeliveryGame -- "
             "or '@path/to/file.json' to read it from a file instead (recommended "
             "on Windows, where quoting embedded double quotes is unreliable)",
    )
    parser.add_argument(
        "--timeout", type=float, default=1.0,
        help="seconds allowed per decide() call, INCLUDING interpreter startup for the sandbox subprocess "
             "(default 1.0 -- lower it once you've confirmed bots run comfortably under that on your machine)",
    )
    parser.add_argument("--width", type=int, default=21, help="board width")
    parser.add_argument("--height", type=int, default=21, help="board height")
    parser.add_argument("--finale", action="store_true", help="also run one all-vs-all free-for-all match")
    args = parser.parse_args()

    game_cls = load_class(args.game)
    game_kwargs = {"width": args.width, "height": args.height, **_load_game_kwargs(args.game_kwargs)}

    bots, errors = load_bots(args.bots_dir)
    for err in errors:
        print(f"WARNING: skipping {err}")

    if len(bots) < 2:
        raise SystemExit("Need at least 2 valid bots to run a tournament.")

    print(f"Game: {args.game}")
    print(f"Loaded {len(bots)} bots: {', '.join(bots)}\n")

    out_dir = Path(args.out)
    leaderboard, match_log = round_robin(
        bots, game_cls, game_kwargs, timeout=args.timeout, replay_dir=str(out_dir / "replays")
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8" explicitly -- don't rely on Windows' locale-
    # dependent default when bot ids/names might contain accents.
    (out_dir / "leaderboard.json").write_text(json.dumps(leaderboard, indent=2), encoding="utf-8")
    (out_dir / "match_log.json").write_text(json.dumps(match_log, indent=2), encoding="utf-8")

    name_width = max((len(row["bot"]) for row in leaderboard), default=4) + 2
    print(f"{'bot':<{name_width}}{'wins':<8}{'losses':<8}{'draws':<8}")
    for row in leaderboard:
        print(f"{row['bot']:<{name_width}}{row['wins']:<8}{row['losses']:<8}{row['draws']:<8}")

    if args.finale:
        finale_kwargs = {**game_kwargs, "width": max(args.width, 6 * len(bots)), "height": max(args.height, 6 * len(bots))}
        winners = free_for_all(
            bots, game_cls, finale_kwargs, timeout=args.timeout,
            replay_path=str(out_dir / "replays" / "finale.json"),
        )
        print(f"\nFinale winner: {winners[0] if len(winners) == 1 else winners or 'draw -- nobody scored'}")

    print(f"\nFull results in {out_dir}/  (leaderboard.json, match_log.json, replays/)")
    print("Open viewer/replay_viewer.html in a browser and load a file from replays/ to watch a match.")


if __name__ == "__main__":
    main()