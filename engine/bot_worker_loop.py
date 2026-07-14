"""Long-lived worker process: one of these is launched per bot for the
whole match (see engine/persistent_sandbox.py), instead of a fresh
subprocess per single move. This is what lets a bot's __init__ run once
and its self.xxx attributes genuinely persist between turns, the same
way an ordinary long-running Python program works.

Protocol: the first line on stdin is a JSON header naming the bot file
and the game class to use. Every line after that is one turn's
serialized view; this process replies with exactly one line of JSON per
turn -- {"ok": true, "action": ...} or {"ok": false} if decide() raised
or returned something the game's serialize_action rejected -- and keeps
looping until stdin is closed (the parent closes it at the end of the
match).

A single per-turn exception does not end this process -- it's caught,
reported as a forfeit for that turn only, and the loop continues, since
the bot might behave fine again next turn (an exception caused by this
turn's specific state isn't evidence the whole process is broken). A
genuine *hang* can't be detected from in here at all -- that's handled
entirely on the parent side (engine/persistent_sandbox.py), which kills
this process outright if a reply doesn't arrive in time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.game_loader import load_class  # noqa: E402
from engine.loader import load_bot_class_from_path  # noqa: E402


def main() -> int:
    header_line = sys.stdin.readline()
    if not header_line:
        return 1
    header = json.loads(header_line)

    game_cls = load_class(header["game_cls_path"])
    bot_cls = load_bot_class_from_path(header["bot_path"])
    bot = bot_cls()  # instantiated ONCE for the whole match -- this is the whole point

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        try:
            view = game_cls.deserialize_view(payload["view"])
            move = bot.decide(view)
            serialized = game_cls.serialize_action(move)
            print(json.dumps({"ok": True, "action": serialized}), flush=True)
        except Exception:
            print(json.dumps({"ok": False}), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
