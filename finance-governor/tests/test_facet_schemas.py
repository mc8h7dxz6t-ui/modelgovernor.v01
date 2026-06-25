"""Facet schema validation tests."""
from __future__ import annotations

import pytest

from platforms.common.facet_schemas import FacetValidationError, validate_facets


def test_wire_match_requires_amount():
    validate_facets("wire_match", {"amount": "100.00"})
    with pytest.raises(FacetValidationError, match="amount"):
        validate_facets("wire_match", {"currency": "USD"})


def test_credit_govern_requires_core_facets():
    validate_facets(
        "credit_govern",
        {
            "application_id": "app-1",
            "exposure_amount": "50000.00",
            "model_version_id": "v3",
        },
    )


def test_unknown_platform_skips_validation():
    validate_facets("custom_platform", {})


def test_type_validation():
    with pytest.raises(FacetValidationError, match="string"):
        validate_facets("wire_match", {"amount": 100})
