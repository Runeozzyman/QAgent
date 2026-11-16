"""Read an OpenAPI spec and turn it into QAgent models.

Typical use::

    from qagent.spec import load_spec
    spec = load_spec("http://localhost:8000/openapi.json")
    for endpoint in spec.endpoints:
        print(endpoint.key)
"""

from __future__ import annotations

from pathlib import Path

from qagent.models import ApiSpec
from qagent.spec.errors import (
    RefResolutionError,
    SpecError,
    SpecLoadError,
    SpecValidationError,
)
from qagent.spec.loader import load_document
from qagent.spec.parser import parse_document
from qagent.spec.refs import resolve_refs
from qagent.spec.validate import validate_document

__all__ = [
    "RefResolutionError",
    "SpecError",
    "SpecLoadError",
    "SpecValidationError",
    "load_spec",
]


def load_spec(source: str | Path, *, strict: bool = True) -> ApiSpec:
    """Load, validate, resolve and parse a spec in one call.

    Validation runs before ``$ref`` resolution so error locations match the
    file the user wrote.
    """
    document = load_document(source)
    validate_document(document, strict=strict)
    return parse_document(resolve_refs(document))
