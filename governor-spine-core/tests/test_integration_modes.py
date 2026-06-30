"""Tests for integration mode boundaries."""

from __future__ import annotations

import os
from unittest import mock

from spine_core.integration_modes import IntegrationMode, is_sandbox_mode, payment_rail_mode


def test_payment_rail_defaults_to_sandbox() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        assert payment_rail_mode() == IntegrationMode.SANDBOX


def test_stub_alias_is_sandbox() -> None:
    with mock.patch.dict(os.environ, {"PAYMENT_RAIL_MODE": "stub"}, clear=False):
        assert payment_rail_mode() == IntegrationMode.SANDBOX
        assert is_sandbox_mode("stub")


def test_fednow_is_live() -> None:
    with mock.patch.dict(os.environ, {"PAYMENT_RAIL_MODE": "fednow"}, clear=False):
        assert payment_rail_mode() == IntegrationMode.LIVE
