from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

HAS_VALIDATOR = importlib.util.find_spec("openapi_spec_validator") is not None
needs_validator = pytest.mark.skipif(
    not HAS_VALIDATOR, reason="openapi-spec-validator is not installed"
)


@pytest.fixture
def petstore_path() -> Path:
    return FIXTURES / "petstore.yaml"


@pytest.fixture
def minibank_path() -> Path:
    return FIXTURES / "minibank.json"
