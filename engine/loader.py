"""Discovers bot files in a directory and imports each one.

Convention: one file per student, exactly one `Bot` subclass per file.
The file name (without extension) becomes the bot's id on the
leaderboard -- e.g. `bots/alice.py` becomes bot id `alice`.

Loading never raises on a single broken submission. A file that fails
to import, defines zero or several Bot subclasses, or can't be
instantiated is skipped and reported as an error string; the tournament
proceeds with whichever bots did load cleanly. This means one student's
typo on submission day never cancels the tournament for everyone else.
"""
from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from engine.bot import Bot


@dataclass
class LoadedBot:
    bot_id: str
    path: str          # absolute path to the .py file -- the sandbox
                        # re-imports from this path fresh on every single
                        # decide() call, so the live `instance` below is
                        # only used for things like reading bot.name, not
                        # for actually playing matches.
    instance: Bot


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build an import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _find_bot_class(module, module_name: str):
    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Bot) and obj is not Bot and obj.__module__ == module_name
    ]
    return candidates


def load_bots(bots_dir: str) -> Tuple[Dict[str, LoadedBot], List[str]]:
    """Returns (bots, errors).

    `bots` maps bot_id -> LoadedBot (instance + the file path it came
    from). `errors` is a list of human-readable strings, one per file
    that could not be loaded, e.g. "alice.py: no Bot subclass found".
    """
    bots: Dict[str, LoadedBot] = {}
    errors: List[str] = []

    bots_path = Path(bots_dir)
    if not bots_path.is_dir():
        return bots, [f"{bots_dir}: no such directory"]

    for path in sorted(bots_path.glob("*.py")):
        if path.name.startswith("_"):
            continue  # underscore-prefixed files are helpers, not bots

        try:
            module = _load_module(path)
        except Exception as exc:  # noqa: BLE001 -- student code, catch everything
            errors.append(f"{path.name}: failed to import ({exc!r})")
            continue

        candidates = _find_bot_class(module, path.stem)

        if len(candidates) == 0:
            errors.append(f"{path.name}: no Bot subclass found")
            continue
        if len(candidates) > 1:
            names = ", ".join(c.__name__ for c in candidates)
            errors.append(f"{path.name}: multiple Bot subclasses found ({names}) -- keep one per file")
            continue

        try:
            instance = candidates[0]()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.name}: could not instantiate ({exc!r})")
            continue

        bots[path.stem] = LoadedBot(bot_id=path.stem, path=str(path.resolve()), instance=instance)

    return bots, errors
