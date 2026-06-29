"""FNOL + FedNow sandbox integration tests — live mock servers (Wave 3 A3/A4)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from decimal import Decimal
from pathlib import Path

import pytest

from platforms.common.integrations.bank_rail import dispatch_payment
from platforms.common.integrations.fnol_writeback import sync_fnol_decision
from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus

IG_ROOT = Path(__file__).resolve().parents[1]


def _wait_for_url(url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


@pytest.fixture
def fednow_sandbox_server():
    proc = subprocess.Popen(
        [sys.executable, str(IG_ROOT / "scripts" / "mock_fednow_sandbox.py")],
        env={**os.environ, "FEDNOW_SANDBOX_PORT": "8192"},
    )
    try:
        _wait_for_url("http://127.0.0.1:8192/v1/payments")
        yield "http://127.0.0.1:8192/v1/payments"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture
def pas_writeback_sandbox_server():
    proc = subprocess.Popen(
        [sys.executable, str(IG_ROOT / "scripts" / "mock_pas_writeback_sandbox.py")],
        env={**os.environ, "PAS_WRITEBACK_SANDBOX_PORT": "8193"},
    )
    try:
        _wait_for_url("http://127.0.0.1:8193/stats")
        yield "http://127.0.0.1:8193"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_guidewire_writeback_live_sandbox(pas_writeback_sandbox_server: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FNOL_WRITEBACK_MODE", "live")
    monkeypatch.setenv("GUIDEWIRE_WRITEBACK_URL", f"{pas_writeback_sandbox_server}/guidewire/v1/claims/sync")
    result = sync_fnol_decision(
        vendor="guidewire",
        claim_id="GW-SBX-100",
        decision="APPROVED",
        facets={"gate_score": 0.9},
    )
    assert result.status == "synced"
    assert result.dry_run is False
    stats = json.loads(urllib.request.urlopen(f"{pas_writeback_sandbox_server}/stats").read().decode())
    assert any(w["vendor"] == "guidewire" for w in stats["writebacks"])


def test_snapsheet_writeback_live_sandbox(pas_writeback_sandbox_server: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FNOL_WRITEBACK_MODE", "live")
    monkeypatch.setenv("SNAPSHEET_WRITEBACK_URL", f"{pas_writeback_sandbox_server}/snapsheet/v1/claims/sync")
    result = sync_fnol_decision(
        vendor="snapsheet",
        claim_id="SS-SBX-200",
        decision="APPROVED",
        facets={"net_payable": "100.00"},
    )
    assert result.status == "synced"
    stats = json.loads(urllib.request.urlopen(f"{pas_writeback_sandbox_server}/stats").read().decode())
    assert any(w["vendor"] == "snapsheet" for w in stats["writebacks"])


def test_fednow_sandbox_dispatch_live_server(fednow_sandbox_server: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENT_RAIL_MODE", "fednow_sandbox")
    monkeypatch.setenv("FEDNOW_SANDBOX_URL", fednow_sandbox_server)
    monkeypatch.setenv("BANK_RAIL_API_TOKEN", "sandbox-token")
    result = dispatch_payment(
        PaymentInstruction(
            payment_id="pay_sbx_live",
            claim_id="claim-sbx",
            idempotency_key="fednow-live-1",
            amount=Decimal("1.00"),
            currency="USD",
            payee_id="sandbox-payee",
            status=PaymentStatus.PENDING,
        )
    )
    assert result.rail == "fednow_sandbox"
    assert result.external_ref.startswith("fednow-sbx-")
    assert result.status == PaymentStatus.COMPLETED
