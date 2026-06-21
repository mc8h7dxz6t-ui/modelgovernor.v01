from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_sidecar_and_reconciler_modules_import() -> None:
    import_module("sidecar.app.main")
    import_module("reconciler.app.main")


def test_placeholder_scaffold_ready() -> None:
    assert True
