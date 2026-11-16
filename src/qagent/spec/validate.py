"""Check that a document is an OpenAPI 3.x spec before parsing it.

Two layers:

1. Quick structural checks with clear messages for the most common mistakes
   (Swagger 2.0, a missing ``paths`` section, pointing at the wrong file).
2. Full validation with ``openapi-spec-validator``, reduced to one readable line.
"""

from __future__ import annotations

from typing import Any

from qagent.spec.errors import SpecValidationError

SUPPORTED_MAJOR = "3"


def validate_document(document: dict[str, Any], *, strict: bool = True) -> str:
    """Validate ``document`` and return its OpenAPI version string.

    With ``strict=False`` only the quick structural checks run. This is useful
    for slightly non-conforming specs that are still usable.
    """
    version = _check_structure(document)
    if strict:
        _check_with_validator(document)
    return version


def _check_structure(document: dict[str, Any]) -> str:
    if "swagger" in document:
        raise SpecValidationError(
            f"This is a Swagger {document['swagger']} spec. QAgent needs OpenAPI 3.x. "
            "Convert it with https://converter.swagger.io or `swagger2openapi`."
        )

    version = document.get("openapi")
    if version is None:
        raise SpecValidationError(
            "Missing the top-level `openapi` field. Is this an OpenAPI spec?"
        )
    version = str(version)
    if not version.startswith(f"{SUPPORTED_MAJOR}."):
        raise SpecValidationError(f"Unsupported OpenAPI version {version!r}; expected 3.x.")

    info = document.get("info")
    if not isinstance(info, dict) or "title" not in info or "version" not in info:
        raise SpecValidationError("The `info` section must include `title` and `version`.")

    paths = document.get("paths")
    if paths is None and version.startswith("3.0"):
        raise SpecValidationError("The spec has no `paths` section, so there is nothing to test.")
    if paths is not None and not isinstance(paths, dict):
        raise SpecValidationError("`paths` must be an object mapping paths to operations.")
    for path in paths or {}:
        if not str(path).startswith("/"):
            raise SpecValidationError(f"Path {path!r} must start with '/'.")

    return version


def _check_with_validator(document: dict[str, Any]) -> None:
    from openapi_spec_validator import validate

    try:
        validate(document)
    except Exception as exc:  # the library raises several unrelated types
        raise SpecValidationError(_describe_validator_error(exc)) from exc


def _describe_validator_error(exc: Exception) -> str:
    message = getattr(exc, "message", None) or str(exc).splitlines()[0]
    path = getattr(exc, "json_path", None)
    if not path:
        parts = list(getattr(exc, "absolute_path", []) or [])
        path = "/" + "/".join(str(p) for p in parts) if parts else None
    where = f" at {path}" if path and path not in ("$", "/") else ""
    return f"Invalid OpenAPI spec{where}: {message}"
