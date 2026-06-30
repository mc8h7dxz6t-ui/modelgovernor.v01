#!/usr/bin/env python3
"""Build, tag, push, and record container image promotion."""
from __future__ import annotations

import argparse
import json
import os
import shutil
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
    env_sha = os.environ.get("GIT_SHA", "").strip()
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _run(cmd: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(cmd), flush=True)
    if not dry_run:
        subprocess.check_call(cmd, cwd=ROOT)


def _image_digest(ref: str) -> str | None:
    try:
        raw = subprocess.check_output(
            ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", ref],
            cwd=ROOT,
            text=True,
        ).strip()
        if raw and "@" in raw:
            return raw.split("@", 1)[1]
        image_id = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.Id}}", ref],
            cwd=ROOT,
            text=True,
        ).strip()
        if image_id.startswith("sha256:"):
            return image_id.split(":", 1)[1]
        return image_id or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _scan_image(ref: str, *, severity: str) -> None:
    if not shutil.which("trivy"):
        raise RuntimeError("trivy not found in PATH — install before --scan")
    _run(
        [
            "trivy",
            "image",
            "--severity",
            severity,
            "--ignore-unfixed",
            "--exit-code",
            "1",
            ref,
        ],
        dry_run=False,
    )


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
    parser.add_argument("--scan", action="store_true", help="Run Trivy scan (CRITICAL,HIGH) after each build")
    parser.add_argument(
        "--scan-severity",
        default=os.environ.get("TRIVY_SEVERITY", "CRITICAL,HIGH"),
        help="Trivy severity filter",
    )
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

    if args.dry_run:
        paths = write_promotion_artifacts(plan, args.out_dir)
        print(json.dumps({"artifacts": paths, "immutable_tag": plan["immutable_tag"]}, indent=2))
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
            if args.scan:
                _scan_image(immutable_ref, severity=args.scan_severity)
            if args.push:
                _run(["docker", "push", immutable_ref], dry_run=False)
                _run(["docker", "push", env_ref], dry_run=False)
            img["digest"] = _image_digest(immutable_ref) or ""
        print(f"OK  promoted {gov_key} ({len(spec['images'])} images)", flush=True)

    plan["scanned"] = args.scan
    plan["pushed"] = args.push
    paths = write_promotion_artifacts(plan, args.out_dir)
    print(json.dumps({"artifacts": paths, "immutable_tag": plan["immutable_tag"], "pushed": args.push}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
