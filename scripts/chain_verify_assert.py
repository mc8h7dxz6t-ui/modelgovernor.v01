#!/usr/bin/env python3
"""Shell-friendly chain verification assert (reads JSON from stdin)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "governor-spine-core"))

from spine_core.chain_verify_assert import assert_chain_verified  # noqa: E402


def main() -> int:
    payload = json.load(sys.stdin)
    assert_chain_verified(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
