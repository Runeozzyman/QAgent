from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import needs_validator

from qagent.spec.errors import SpecValidationError
from qagent.spec.loader import load_document
from qagent.spec.validate import validate_document


def _doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {},
    }
    doc.update(overrides)
    return doc


def test_minimal_doc_passes_structural_checks() -> None:
    assert validate_document(_doc(), strict=False) == "3.0.3"


def test_swagger_2_gets_conversion_hint() -> None:
    with pytest.raises(SpecValidationError, match="Swagger 2.0.*Convert"):
        validate_document({"swagger": "2.0", "info": {}, "paths": {}}, strict=False)


def test_missing_openapi_field() -> None:
    doc = _doc()
    del doc["openapi"]
    with pytest.raises(SpecValidationError, match="openapi"):
        validate_document(doc, strict=False)


def test_unsupported_version() -> None:
    with pytest.raises(SpecValidationError, match="Unsupported"):
        validate_document(_doc(openapi="4.0.0"), strict=False)


def test_info_needs_title_and_version() -> None:
    with pytest.raises(SpecValidationError, match="info"):
        validate_document(_doc(info={"title": "T"}), strict=False)


def test_missing_paths_in_3_0() -> None:
    doc = _doc()
    del doc["paths"]
    with pytest.raises(SpecValidationError, match="paths"):
        validate_document(doc, strict=False)


def test_paths_optional_in_3_1() -> None:
    doc = _doc(openapi="3.1.0", webhooks={})
    del doc["paths"]
    assert validate_document(doc, strict=False) == "3.1.0"


def test_path_must_start_with_slash() -> None:
    with pytest.raises(SpecValidationError, match="start with '/'"):
        validate_document(_doc(paths={"users": {}}), strict=False)


@needs_validator
def test_full_validation_accepts_fixtures(petstore_path: Path, minibank_path: Path) -> None:
    validate_document(load_document(petstore_path))
    validate_document(load_document(minibank_path))


@needs_validator
def test_full_validation_reports_problem() -> None:
    bad = _doc(paths={"/x": {"get": {"responses": "not-an-object"}}})
    with pytest.raises(SpecValidationError, match="Invalid OpenAPI spec"):
        validate_document(bad)
