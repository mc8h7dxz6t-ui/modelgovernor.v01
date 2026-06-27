"""Repository integrity checks — spine and platform Dockerfile/compose port alignment."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from spine_core.config import DOMAIN_PORTS, GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]

# Authoritative platform listen ports per vertical (EXPOSE / uvicorn --port)
PLATFORM_PORTS: dict[GovernorDomain, frozenset[int]] = {
    GovernorDomain.FINANCE: frozenset({8093, 8094, 8095, 8096, 8097}),
    GovernorDomain.INSURANCE: frozenset({8103, 8104, 8105, 8106, 8107, 8108, 8109, 8110, 8111, 8112, 8113}),
    GovernorDomain.CYBER: frozenset({8123, 8124, 8125, 8126, 8127, 8128, 8129, 8130, 8131}),
}

DOMAIN_COMPOSE: dict[GovernorDomain, Path] = {
    GovernorDomain.MODEL: REPO_ROOT / "docker-compose.demo.yml",
    GovernorDomain.FINANCE: REPO_ROOT / "finance-governor/docker-compose.yml",
    GovernorDomain.INSURANCE: REPO_ROOT / "insurance-governor/docker-compose.yml",
    GovernorDomain.CYBER: REPO_ROOT / "cybersecurity-governor/docker-compose.yml",
}

DOMAIN_ROOT: dict[GovernorDomain, Path] = {
    GovernorDomain.FINANCE: REPO_ROOT / "finance-governor",
    GovernorDomain.INSURANCE: REPO_ROOT / "insurance-governor",
    GovernorDomain.CYBER: REPO_ROOT / "cybersecurity-governor",
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


@dataclass
class PlatformPortDrift:
    dockerfile: str
    exposed_port: int
    allowed_ports: frozenset[int]


def _extract_uvicorn_port(dockerfile: Path) -> int | None:
    if not dockerfile.is_file():
        return None
    text = dockerfile.read_text()
    match = re.search(r'--port",\s*"(\d+)"', text)
    return int(match.group(1)) if match else None


def _extract_listen_ports(dockerfile: Path) -> list[int]:
    if not dockerfile.is_file():
        return []
    text = dockerfile.read_text()
    ports = [int(p) for p in re.findall(r"^EXPOSE\s+(\d+)\s*$", text, re.MULTILINE)]
    ports.extend(int(p) for p in re.findall(r'--port",\s*"(\d+)"', text))
    return ports


def _extract_compose_publish(compose: Path, container_port: int) -> int | None:
    if not compose.is_file():
        return None
    for line in compose.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(f'- "{container_port}:{container_port}"'):
            return container_port
        match = re.match(rf'-\s*"(\d+):{container_port}"', stripped)
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


def check_platform_dockerfile_ports() -> list[PlatformPortDrift]:
    drifts: list[PlatformPortDrift] = []
    for domain in (GovernorDomain.FINANCE, GovernorDomain.INSURANCE, GovernorDomain.CYBER):
        allowed = PLATFORM_PORTS[domain]
        root = DOMAIN_ROOT[domain] / "platforms"
        if not root.is_dir():
            continue
        for dockerfile in root.glob("**/Dockerfile"):
            for port in _extract_listen_ports(dockerfile):
                if port not in allowed:
                    drifts.append(
                        PlatformPortDrift(
                            dockerfile=str(dockerfile.relative_to(REPO_ROOT)),
                            exposed_port=port,
                            allowed_ports=allowed,
                        )
                    )
    return drifts


def port_alignment_failures() -> list[str]:
    failures: list[str] = []
    for result in check_spine_port_alignment():
        if not result.ok:
            failures.append(
                f"{result.domain.name} {result.service}: expected {result.expected}, "
                f"dockerfile={result.dockerfile_port}, compose={result.compose_port}"
            )
    for drift in check_platform_dockerfile_ports():
        failures.append(
            f"{drift.dockerfile}: EXPOSE {drift.exposed_port} not in allowed {sorted(drift.allowed_ports)}"
        )
    return failures


def main() -> int:
    failures = port_alignment_failures()
    if failures:
        print("PORT ALIGNMENT FAILURE", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("Port check validation passed: spine + platform EXPOSE ports align with governor-spine-core map.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
