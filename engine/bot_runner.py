"""Standalone entry point invoked by engine/sandbox.py in a fresh
subprocess. Not meant to be run by hand.

Reads a JSON payload from stdin: which bot file to load, which Game
class to use to reconstruct the view, and the serialized view itself.
Re-imports the bot fresh from its file path (this is the whole point --
no live Python object ever crosses the process boundary, so this works
identically whether the parent process is using fork, spawn, or
forkserver under the hood). Prints the chosen Move's name to stdout on
success; prints nothing and exits non-zero on any failure (crash,
invalid return value, anything).
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.bot import Bot  # noqa: E402
from engine.game_loader import load_class  # noqa: E402


def _load_bot_class(bot_path: str):
    path = Path(bot_path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build an import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Bot) and obj is not Bot and obj.__module__ == module.__name__
    ]
    if not candidates:
        raise ImportError(f"no Bot subclass found in {bot_path}")
    return candidates[0]


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw)

    try:
        bot_cls = _load_bot_class(payload["bot_path"])
        game_cls = load_class(payload["game_cls_path"])
        view = game_cls.deserialize_view(payload["view"])
        bot = bot_cls()
        move = bot.decide(view)
        serialized = game_cls.serialize_action(move)
    except Exception:
        return 1

    sys.stdout.write(json.dumps(serialized))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
