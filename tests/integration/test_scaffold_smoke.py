from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _import_service_main(service_dir: str) -> None:
    service_path = str(Path(__file__).resolve().parents[2] / service_dir)
    sys.path.insert(0, service_path)
    try:
        for module_name in list(sys.modules):
            if module_name == "app" or module_name.startswith("app."):
                sys.modules.pop(module_name)
        import_module("app.main")
    finally:
        sys.path.pop(0)


def test_sidecar_and_reconciler_modules_import() -> None:
    _import_service_main("sidecar")
    _import_service_main("reconciler")


def test_placeholder_scaffold_ready() -> None:
    assert True
