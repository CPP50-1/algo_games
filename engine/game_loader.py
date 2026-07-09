"""One tiny shared helper: dynamically import a class given a string
like "games.tron:TronGame". Used by run_tournament.py, validate_ci.py,
and bot_runner.py so all three agree on the exact same convention for
naming a game module on the command line.
"""
from __future__ import annotations

import importlib


def load_class(dotted_path: str):
    module_name, class_name = dotted_path.split(":")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
