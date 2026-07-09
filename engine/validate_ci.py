"""CI smoke test, run on every pull request.

Every bot file in the target folder must import cleanly and survive one
call to decide() against a fixed dummy board, inside a generous timeout.
This does not judge strategy or code quality -- only "does it run" -- so
a passing check just means the submission is safe to include in
tournament day, not that it's any good.

Usage:
    python engine/validate_ci.py --bots-dir bots --game games.tron:TronGame
    python engine/validate_ci.py --bots-dir bots_delivery --game games.delivery:DeliveryGame
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.loader import load_bots  # noqa: E402
from engine.sandbox import call_with_timeout  # noqa: E402
from engine.game_loader import load_class  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bots-dir", default="bots")
    parser.add_argument("--game", default="games.tron:TronGame")
    parser.add_argument("--width", type=int, default=15)
    parser.add_argument("--height", type=int, default=15)
    args = parser.parse_args()

    game_cls = load_class(args.game)
    bots, errors = load_bots(args.bots_dir)
    for err in errors:
        print(f"FAIL: {err}")

    if not bots:
        print(f"FAIL: no valid bots found in {args.bots_dir}/")
        return 1

    ok = not errors

    for bot_id, loaded in bots.items():
        game = game_cls(width=args.width, height=args.height)
        game.setup([bot_id, "_dummy_opponent_"])
        move = call_with_timeout(game, args.game, loaded.path, game.view_for(bot_id), timeout=3.0)
        if move is None:
            print(f"FAIL: {bot_id} crashed, timed out, or returned something invalid")
            ok = False
        else:
            print(f"OK: {bot_id} responded with {move}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
