"""PostureReconcile — CVE / patch-lag drift blocks runtime security commits."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="posturereconcile", version="0.1.0")
_GOVERNED = GovernedPlatform("posture_reconcile")


class PostureRecord(BaseModel):
    asset_id: str
    cve_count: int = 0
    patch_lag_days: int = 0
    critical_cves: int = 0
    account_id: str = "tenant-default"


def _patch_lag_threshold() -> int:
    return int(os.environ.get("POSTURE_PATCH_LAG_DAYS", "30"))


def _critical_cve_threshold() -> int:
    return int(os.environ.get("POSTURE_CRITICAL_CVE_THRESHOLD", "1"))


def evaluate_posture(rec: PostureRecord) -> tuple[str, str]:
    if rec.critical_cves >= _critical_cve_threshold() or rec.patch_lag_days > _patch_lag_threshold():
        increment_invariant("posture_reconcile", "posture_drift_total")
        if rec.critical_cves >= _critical_cve_threshold():
            increment_invariant("posture_reconcile", "posture_cve_threshold_breach_total")
        return "DRIFT", f"cves={rec.critical_cves},lag={rec.patch_lag_days}"
    increment_invariant("posture_reconcile", "posture_matched_total")
    return "MATCHED", "posture within tolerance"


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("posture_reconcile")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/posture/evaluate")
@app.post("/posture/ingest")
def ingest(request: PostureRecord) -> dict:
    match_state, reference = evaluate_posture(request)
    facets = {
        "asset_id": request.asset_id,
        "cve_count": request.cve_count,
        "patch_lag_days": request.patch_lag_days,
        "critical_cves": request.critical_cves,
        "match_state": match_state,
        "reference": reference,
    }
    crystal_id = _GOVERNED.govern_operation(
        f"posture-{request.asset_id}",
        facets,
        decision=match_state,
        reserve_amount="0",
        account_id=request.account_id,
        outcome=match_state.lower(),
    )
    if match_state == "DRIFT":
        raise HTTPException(status_code=422, detail={"match_state": match_state, "reference": reference})
    return {"match_state": match_state, "crystal_id": crystal_id, "reference": reference}
