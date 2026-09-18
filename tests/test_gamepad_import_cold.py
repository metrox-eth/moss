"""The dimOS wrapper must import when its optional dependencies are present; only their absence may skip."""
import importlib

import pytest


def test_gamepad_module_imports_or_skips_only_for_optional_deps():
    try:
        mod = importlib.import_module("moss_dimos.gamepad")
    except ModuleNotFoundError as e:
        if e.name and (e.name == "dimos" or e.name.startswith("dimos.") or e.name == "pygame"):
            pytest.skip(f"optional dependency missing: {e.name}")
        raise
    assert hasattr(mod, "GamepadTeleop")
