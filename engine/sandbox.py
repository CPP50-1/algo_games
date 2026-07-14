"""Runs a single bot's decide() call in its own fresh subprocess with a
hard timeout, then exits -- a one-shot alternative to
engine/persistent_sandbox.py, which is what actual matches use (see
engine/match.py). This one-shot version is now only used by
engine/validate_ci.py's smoke test, where a single sanity-check call
against a dummy board is all that's needed and there's no reason to pay
for a bot's process to stick around afterward.

Implementation note: this uses subprocess.run() with a small runner
script (engine/bot_runner.py), not Python's multiprocessing module.
multiprocessing needs to pickle the live bot object across the process
boundary. On Linux/macOS that mostly works because the default "fork"
start method just copies the parent's memory. On Windows, the default
"spawn" start method starts a brand-new interpreter and has to reimport
everything by name -- which fails for bots loaded dynamically from an
arbitrary folder, since they were never installed as a real importable
package. subprocess.run avoids the whole problem: the child re-imports
the bot straight from its file path, and only plain JSON crosses the
process boundary. Same protection against hangs, and it behaves
identically on every OS. engine/persistent_sandbox.py follows this same
"never pickle a live object" rule, just keeps its subprocess alive
across many calls instead of one.

Actions are game-defined, not hardcoded to any one type: whatever
decide() returns is converted with the game's own serialize_action /
deserialize_action (see games/base.py) rather than assuming everything
is a Move. That's what lets a turn-based game like Connect Four return
a plain column index instead of a direction.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from engine.game_loader import load_class

_RUNNER = str(Path(__file__).resolve().parent / "bot_runner.py")


def call_with_timeout(
    game: Any,
    game_cls_path: str,
    bot_path: str,
    view: Any,
    timeout: float,
) -> Optional[Any]:
    """Returns whatever action the bot chose (already deserialized into
    the game's own action type), or None if it timed out, crashed, or
    returned something the game rejected -- None always means "forfeit
    this turn" to the caller, which is up to the game module to
    interpret.

    `game_cls_path` is "module.path:ClassName" for the Game subclass in
    use (e.g. "games.tron:TronGame") -- it's how the subprocess knows
    which (de)serializers to call, without needing a live Game object.
    `bot_path` is the absolute path to the bot's .py file.
    """
    payload = json.dumps({
        "game_cls_path": game_cls_path,
        "bot_path": bot_path,
        "view": game.serialize_view(view),
    })

    try:
        proc = subprocess.run(
            [sys.executable, _RUNNER],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        # Covers rare platform-specific process-launch failures (e.g. a
        # transient WinError while spawning) -- treat as a forfeit
        # rather than crashing the whole tournament.
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        return None

    try:
        game_cls = load_class(game_cls_path)
        return game_cls.deserialize_action(json.loads(proc.stdout))
    except Exception:
        return None
