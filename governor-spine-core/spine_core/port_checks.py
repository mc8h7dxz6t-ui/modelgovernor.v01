"""Repository integrity checks — Dockerfile listen ports vs compose publish ports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from spine_core.config import DOMAIN_PORTS, GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]

DOMAIN_COMPOSE: dict[GovernorDomain, Path] = {
    GovernorDomain.MODEL: REPO_ROOT / "docker-compose.demo.yml",
    GovernorDomain.FINANCE: REPO_ROOT / "finance-governor/docker-compose.yml",
    GovernorDomain.INSURANCE: REPO_ROOT / "insurance-governor/docker-compose.yml",
    GovernorDomain.CYBER: REPO_ROOT / "cybersecurity-governor/docker-compose.yml",
}

DOMAIN_DOCKERFILES: dict[GovernorDomain, tuple[Path, Path]] = {
    GovernorDomain.FINANCE: (
        REPO_ROOT / "finance-governor/spine/gateway/Dockerfile",
        REPO_ROOT / "finance-governor/spine/sidecar/Dockerfile",
    ),
    GovernorDomain.INSURANCE: (
        REPO_ROOT / "insurance-governor/spine/gateway/Dockerfile",
        REPO_ROOT / "insurance-governor/spine/sidecar/Dockerfile",
    ),
    GovernorDomain.CYBER: (
        REPO_ROOT / "cybersecurity-governor/spine/gateway/Dockerfile",
        REPO_ROOT / "cybersecurity-governor/spine/sidecar/Dockerfile",
    ),
}


@dataclass
class PortCheckResult:
    domain: GovernorDomain
    service: str
    expected: int
    dockerfile_port: int | None
    compose_port: int | None

    @property
    def ok(self) -> bool:
        return self.dockerfile_port == self.expected and self.compose_port == self.expected


def _extract_uvicorn_port(dockerfile: Path) -> int | None:
    if not dockerfile.is_file():
        return None
    text = dockerfile.read_text()
    match = re.search(r'--port",\s*"(\d+)"', text)
    return int(match.group(1)) if match else None


def _extract_compose_publish(compose: Path, host_port: int) -> int | None:
    if not compose.is_file():
        return None
    for line in compose.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(f'- "{host_port}:{host_port}"'):
            return host_port
        match = re.match(rf'-\s*"(\d+):{host_port}"', stripped)
        if match:
            return int(match.group(1))
    return None


def check_spine_port_alignment() -> list[PortCheckResult]:
    results: list[PortCheckResult] = []
    for domain in (GovernorDomain.FINANCE, GovernorDomain.INSURANCE, GovernorDomain.CYBER):
        ports = DOMAIN_PORTS[domain]
        gw_df, sc_df = DOMAIN_DOCKERFILES[domain]
        compose = DOMAIN_COMPOSE[domain]
        for service, expected, df in (
            ("gateway", ports.gateway, gw_df),
            ("sidecar", ports.sidecar, sc_df),
        ):
            results.append(
                PortCheckResult(
                    domain=domain,
                    service=service,
                    expected=expected,
                    dockerfile_port=_extract_uvicorn_port(df),
                    compose_port=_extract_compose_publish(compose, expected),
                )
            )
    return results


def port_alignment_failures() -> list[str]:
    failures: list[str] = []
    for result in check_spine_port_alignment():
        if result.ok:
            continue
        failures.append(
            f"{result.domain.name} {result.service}: expected {result.expected}, "
            f"dockerfile={result.dockerfile_port}, compose={result.compose_port}"
        )
    return failures
