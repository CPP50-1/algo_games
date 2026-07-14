"""Manages one long-lived subprocess per bot for the duration of a
single match, instead of spawning a fresh subprocess for every single
move (see engine/sandbox.py for that simpler, one-shot-per-call
approach -- still used by engine/validate_ci.py, where a single
sanity-check call is all that's needed).

This is what makes persistent bot state (ordinary self.xxx attributes
set in __init__) actually work: the same bot *instance*, in the same
living process, answers every turn of the match, rather than a fresh
instance being created from scratch every single time.

The trade-off: enforcing a per-turn timeout against a long-lived
process is trickier than subprocess.run(timeout=...) on a one-shot
call, since a blocking read on a pipe has no portable timeout of its
own. This uses a background daemon thread that continuously reads
lines from the subprocess's stdout into a queue.Queue, so the main
thread can enforce a timeout with a plain Queue.get(timeout=...) --
which behaves identically on Windows, macOS, and Linux, unlike
select()/selectors on OS pipes (select() does not reliably support
pipes on Windows at all, only sockets).

Safety rule: if a bot's process ever times out, it is killed
immediately and marked dead for the rest of the match -- every
subsequent turn becomes an automatic forfeit (None) without ever trying
to relaunch it. A hang once means it can hang again; there's no way to
know a restarted process would behave any better, so it's safer to
treat a timeout as fatal for that one match than risk it stalling again
on a later, more consequential turn.
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Optional

_WORKER = str(Path(__file__).resolve().parent / "bot_worker_loop.py")


class PersistentBotProcess:
    def __init__(self, bot_path: str, game_cls_path: str) -> None:
        self._dead = False
        self._proc = subprocess.Popen(
            [sys.executable, _WORKER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,  # line-buffered
        )
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        header = json.dumps({"bot_path": bot_path, "game_cls_path": game_cls_path})
        if not self._write_line(header):
            self._kill()

    def _read_loop(self) -> None:
        try:
            for line in self._proc.stdout:
                self._queue.put(line)
        except Exception:
            pass  # process died / pipe closed -- the next ask() will time out and handle it

    def _write_line(self, line: str) -> bool:
        try:
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()
            return True
        except Exception:
            return False

    def ask(self, game: Any, view: Any, timeout: float) -> Optional[Any]:
        """Returns the bot's chosen action (already deserialized into
        the game's own action type), or None if it's already dead from
        an earlier turn, times out this turn (which also kills it from
        here on), raised inside decide(), or returned something the
        game's serialize_action rejected. None always means "forfeit
        this turn" to the caller.
        """
        if self._dead:
            return None

        payload = json.dumps({"view": game.serialize_view(view)})
        if not self._write_line(payload):
            self._kill()
            return None

        try:
            line = self._queue.get(timeout=timeout)
        except queue.Empty:
            self._kill()  # genuinely hung -- never trust this process again this match
            return None

        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            return None  # malformed output -- forfeit this turn only, process may still be fine

        if not response.get("ok"):
            return None  # decide() raised or returned an invalid action -- forfeit this turn only

        try:
            return type(game).deserialize_action(response["action"])
        except Exception:
            return None

    def _kill(self) -> None:
        self._dead = True
        try:
            self._proc.kill()
        except Exception:
            pass

    def close(self) -> None:
        """Call once at the end of a match to clean up the subprocess."""
        if self._dead:
            return
        try:
            self._proc.stdin.close()
        except Exception:
            pass
        try:
            self._proc.wait(timeout=2.0)
        except Exception:
            self._kill()
