#!/usr/bin/env bash
# Scaffold a new plug-and-play Cybersecurity Governor platform
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <platform_name> [port]"
  exit 1
fi

NAME="$1"
PORT="${2:-8110}"
DISPLAY="$(echo "$NAME" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2));}1')"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/platforms/$NAME"

if [[ -d "$DIR" ]]; then
  echo "Platform already exists: $DIR"
  exit 1
fi

mkdir -p "$DIR"

cat > "$DIR/manifest.yaml" <<EOF
name: $NAME
display_name: $DISPLAY
default_policy_id: ${NAME//_/-}-us
default_risk_tier: high
port: $PORT
required_facet_keys:
  - operation_id
commit_decisions:
  - APPROVED
EOF

cat > "$DIR/main.py" <<'PY'
"""Platform scaffold — implement domain gate logic in gate.py."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

app = FastAPI(title="PLATFORM_NAME", version="0.1.0")
_GOVERNED = GovernedPlatform("PLATFORM_NAME")


class EvaluateRequest(BaseModel):
    operation_id: str
    facets: dict


class EvaluateResponse(BaseModel):
    operation_id: str
    decision: str
    crystal_id: str | None = None


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("PLATFORM_NAME")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
  decision = "APPROVED"
  crystal_id = _GOVERNED.govern_operation(
      request.operation_id,
      request.facets,
      decision=decision,
      reserve_amount="0",
  )
  return EvaluateResponse(operation_id=request.operation_id, decision=decision, crystal_id=crystal_id)
PY
sed -i "s/PLATFORM_NAME/$NAME/g" "$DIR/main.py"

cat > "$DIR/Dockerfile" <<EOF
FROM python:3.12-slim
WORKDIR /app/cybersecurity-governor
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/cybersecurity-governor
COPY cybersecurity-governor/platforms/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY cybersecurity-governor/platforms/common ./platforms/common
COPY cybersecurity-governor/platforms/$NAME ./platforms/$NAME
EXPOSE $PORT
CMD ["uvicorn", "platforms.$NAME.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
EOF

cat > "$DIR/docker-compose.standalone.yml" <<EOF
services:
  $NAME:
    build:
      context: ../..
      dockerfile: cybersecurity-governor/platforms/$NAME/Dockerfile
    environment:
      CG_SPINE_ENABLED: "false"
    ports:
      - "$PORT:$PORT"
EOF

echo "Scaffolded $DIR"
echo "Next: add to platforms/registry.yaml, migrations policy seed, Helm values.platforms"
