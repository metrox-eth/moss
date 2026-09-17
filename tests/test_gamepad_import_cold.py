"""The derived gamepad module must at least import and expose its pure helpers (no pad, no dimOS run)."""
import importlib

import pytest


def test_gamepad_module_imports_or_skips_without_dimos():
    try:
        mod = importlib.import_module("moss_dimos.gamepad")
    except ModuleNotFoundError as e:  # dimos / pygame absent on a cold box
        pytest.skip(f"optional dependency missing: {e.name}")
    assert hasattr(mod, "axes_to_twist")
