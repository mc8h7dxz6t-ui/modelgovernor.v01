#!/usr/bin/env python3
"""Build, tag, push, and record container image promotion."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE_CORE = ROOT / "governor-spine-core"
if str(SPINE_CORE) not in sys.path:
    sys.path.insert(0, str(SPINE_CORE))

from spine_core.image_promotion import (  # noqa: E402
    build_promotion_plan,
    manifest_conformance_failures,
    write_promotion_artifacts,
)


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.environ.get("GIT_SHA", "unknown")


def _run(cmd: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(cmd), flush=True)
    if not dry_run:
        subprocess.check_call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote governor container images")
    parser.add_argument(
        "governor",
        choices=["mg", "fg", "ig", "cg", "all", "modelgovernor", "finance-governor", "insurance-governor", "cybersecurity-governor"],
        help="Governor to promote (mg/fg/ig/cg or full name, or all)",
    )
    parser.add_argument(
        "--environment",
        default=os.environ.get("PROMOTION_ENV", "staging"),
        choices=["staging", "production"],
    )
    parser.add_argument(
        "--registry",
        default=os.environ.get(
            "IMAGE_REGISTRY",
            f"ghcr.io/{os.environ.get('GITHUB_REPOSITORY_OWNER', 'modelgovernor').lower()}",
        ),
    )
    parser.add_argument("--git-sha", default=_git_sha())
    parser.add_argument("--push", action="store_true", help="Push images to registry (default: build only)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only; no docker build")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "artifacts" / "image-promotion",
    )
    args = parser.parse_args()

    failures = manifest_conformance_failures(ROOT)
    if failures:
        print("manifest conformance failures:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    plan = build_promotion_plan(
        governor=args.governor,
        registry=args.registry,
        git_sha=args.git_sha,
        environment=args.environment,
        repo_root=ROOT,
    )
    paths = write_promotion_artifacts(plan, args.out_dir)
    print(json.dumps({"artifacts": paths, "immutable_tag": plan["immutable_tag"]}, indent=2))

    if args.dry_run:
        return 0

    for gov_key, spec in plan["governors"].items():
        for img in spec["images"]:
            context = img.get("context", ".")
            dockerfile = img["dockerfile"]
            immutable_ref = img["immutable_ref"]
            env_ref = img["env_ref"]
            _run(
                [
                    "docker",
                    "build",
                    "-f",
                    dockerfile,
                    "-t",
                    immutable_ref,
                    "-t",
                    env_ref,
                    context,
                ],
                dry_run=False,
            )
            if args.push:
                _run(["docker", "push", immutable_ref], dry_run=False)
                _run(["docker", "push", env_ref], dry_run=False)
        print(f"OK  promoted {gov_key} ({len(spec['images'])} images)", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
