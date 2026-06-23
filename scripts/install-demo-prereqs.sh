#!/usr/bin/env bash
# Install or verify demo prerequisites: Docker, Docker Compose, curl, make.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=0
AUTO_INSTALL=0

usage() {
  cat <<'EOF'
Usage: ./scripts/install-demo-prereqs.sh [--check-only] [--install]

Ensures Docker, Docker Compose plugin, curl, and make are available for demos.

  --check-only   Print status and exit non-zero if anything is missing
  --install      Attempt installation on supported Linux distros (requires sudo)
  -h, --help     Show this help

Examples:
  ./scripts/install-demo-prereqs.sh --check-only
  ./scripts/install-demo-prereqs.sh --install
  make demo-prereqs
EOF
}

for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
    --install) AUTO_INSTALL=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

docker_ok() {
  have_cmd docker && docker info >/dev/null 2>&1
}

compose_ok() {
  docker compose version >/dev/null 2>&1
}

missing=()

check_prereqs() {
  missing=()
  have_cmd curl || missing+=("curl")
  have_cmd make || missing+=("make")
  if ! have_cmd docker; then
    missing+=("docker")
  elif ! docker info >/dev/null 2>&1; then
    missing+=("docker (installed but daemon not running — try: sudo systemctl start docker)")
  fi
  if have_cmd docker && ! compose_ok; then
    missing+=("docker compose (Compose plugin)")
  fi
}

print_status() {
  check_prereqs
  echo "Demo prerequisites:"
  if have_cmd curl; then echo "  ✓ curl: $(curl --version | head -n1)"; else echo "  ✗ curl"; fi
  if have_cmd make; then echo "  ✓ make: $(make --version | head -n1)"; else echo "  ✗ make"; fi
  if have_cmd docker; then
    if docker_ok; then
      echo "  ✓ docker: $(docker --version)"
    else
      echo "  ✗ docker: binary present but daemon unavailable"
    fi
  else
    echo "  ✗ docker"
  fi
  if compose_ok; then
    echo "  ✓ docker compose: $(docker compose version)"
  else
    echo "  ✗ docker compose"
  fi
}

install_apt_packages() {
  echo "Installing packages with apt (Docker CE + Compose plugin, curl, make)..."
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl make gnupg
  if ! have_cmd docker; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif ! compose_ok; then
    sudo apt-get install -y docker-compose-plugin
  fi
}

install_dnf_packages() {
  echo "Installing packages with dnf..."
  sudo dnf install -y curl make docker docker-compose-plugin
  sudo systemctl enable --now docker
}

install_prereqs() {
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "Run as a normal user with sudo, not as root." >&2
    exit 1
  fi
  if ! have_cmd sudo; then
    echo "sudo is required for automatic installation." >&2
    exit 1
  fi

  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
  else
    echo "Unsupported OS: cannot auto-install. Install docker, docker compose, curl, and make manually." >&2
    exit 1
  fi

  case "${ID:-}" in
    ubuntu|debian)
      install_apt_packages
      ;;
    fedora|rhel|centos|rocky|almalinux)
      install_dnf_packages
      ;;
    *)
      echo "Unsupported distro '${ID:-unknown}'. Install manually:" >&2
      echo "  - Docker Engine: https://docs.docker.com/engine/install/" >&2
      echo "  - Docker Compose plugin: https://docs.docker.com/compose/install/linux/" >&2
      echo "  - curl, make: your package manager" >&2
      exit 1
      ;;
  esac

  if ! groups "$USER" | grep -q '\bdocker\b'; then
    echo ""
    echo "Adding $USER to the docker group (log out/in or run: newgrp docker)"
    sudo usermod -aG docker "$USER" || true
  fi
  if ! docker_ok; then
    sudo systemctl enable --now docker || true
  fi
}

check_prereqs
print_status

if ((${#missing[@]} == 0)); then
  echo ""
  echo "All demo prerequisites are ready."
  echo "Next: make demo-gold-up && make demo-gold"
  exit 0
fi

echo ""
echo "Missing: ${missing[*]}"

if ((CHECK_ONLY == 1)); then
  echo ""
  echo "Install with: make demo-prereqs-install"
  echo "Or from bash: $REPO_ROOT/scripts/install-demo-prereqs.sh --install"
  exit 1
fi

if ((AUTO_INSTALL == 0)); then
  echo ""
  echo "Re-run with --install to attempt automatic setup."
  exit 1
fi

install_prereqs
check_prereqs
print_status

if ((${#missing[@]} > 0)); then
  echo ""
  echo "Some prerequisites are still missing. You may need to log out/in after docker group changes."
  exit 1
fi

echo ""
echo "Prerequisites installed. Next: make demo-gold-up && make demo-gold"
