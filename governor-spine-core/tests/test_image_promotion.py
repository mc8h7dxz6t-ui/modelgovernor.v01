"""Image promotion manifest and Helm overlay generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from spine_core.image_promotion import (
    build_promotion_plan,
    image_tags,
    iter_image_refs,
    manifest_conformance_failures,
    registry_image,
    render_helm_values_overlay,
    write_promotion_artifacts,
)


def test_manifest_conformance_no_failures():
    root = Path(__file__).resolve().parents[2]
    failures = manifest_conformance_failures(root)
    assert failures == [], "image promotion manifest gaps:\n" + "\n".join(failures)


def test_image_tags_immutable_and_env():
    immutable, env = image_tags(git_sha="abc123def456", environment="staging")
    assert immutable == "sha-abc123def456"
    assert env == "staging-abc123def456"


def test_render_split_style_overlay():
    plan = build_promotion_plan(
        governor="mg",
        registry="ghcr.io/example",
        git_sha="deadbeef",
        environment="production",
    )
    overlay = render_helm_values_overlay(plan, "modelgovernor")
    assert "ghcr.io/example/modelgovernor/sidecar" in overlay
    assert 'tag: "sha-deadbeef"' in overlay
    assert "pullPolicy: Always" in overlay


def test_render_combined_style_overlay():
    plan = build_promotion_plan(
        governor="fg",
        registry="ghcr.io/example",
        git_sha="cafebabe",
        environment="staging",
    )
    overlay = render_helm_values_overlay(plan, "finance-governor")
    assert 'sidecar: "ghcr.io/example/finance-governor/sidecar:sha-cafebabe"' in overlay


def test_write_promotion_artifacts(tmp_path: Path):
    plan = build_promotion_plan(
        governor="mg",
        registry="ghcr.io/example",
        git_sha="abc",
        environment="staging",
    )
    paths = write_promotion_artifacts(plan, tmp_path)
    assert Path(paths["plan"]).is_file()
    assert Path(paths["helm-modelgovernor"]).is_file()


def test_iter_image_refs():
    plan = build_promotion_plan(
        governor="mg",
        registry="ghcr.io/example",
        git_sha="abc123",
        environment="staging",
    )
    refs = iter_image_refs(plan)
    assert len(refs) == 3
    assert refs[0] == "ghcr.io/example/modelgovernor/sidecar:sha-abc123"


def test_iter_image_refs_all_governors():
    plan = build_promotion_plan(
        governor="all",
        registry="ghcr.io/example",
        git_sha="abc123",
        environment="staging",
    )
    refs = iter_image_refs(plan)
    assert len(refs) == 37


def test_registry_image_lowercases():
    ref = registry_image("GHCR.io/Org", "ModelGovernor/Sidecar", "sha-abc")
    assert ref == "ghcr.io/org/modelgovernor/sidecar:sha-abc"
