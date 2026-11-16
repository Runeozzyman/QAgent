"""Plain-data views of a parsed spec, used by `qagent scan`.

Kept separate from the CLI so it can be tested without a terminal.
"""

from __future__ import annotations

from typing import Any

from qagent.models import ApiSpec, Endpoint

SCAN_COLUMNS: tuple[str, ...] = ("Method", "Path", "Auth", "Statuses", "Summary")


def endpoint_row(endpoint: Endpoint) -> tuple[str, ...]:
    if endpoint.requires_auth:
        auth = "required"
    elif endpoint.security:
        auth = "optional"
    else:
        auth = "-"
    summary = endpoint.summary or endpoint.operation_id or ""
    if endpoint.deprecated:
        summary = f"[deprecated] {summary}".strip()
    return (
        endpoint.method,
        endpoint.path,
        auth,
        ", ".join(endpoint.status_codes),
        summary,
    )


def endpoint_rows(spec: ApiSpec) -> list[tuple[str, ...]]:
    return [endpoint_row(e) for e in spec.endpoints]


def scan_summary(spec: ApiSpec) -> dict[str, Any]:
    """A JSON-friendly summary, used by `qagent scan --json`."""
    return {
        "title": spec.title,
        "version": spec.version,
        "openapi": spec.openapi_version,
        "servers": spec.servers,
        "endpoint_count": len(spec.endpoints),
        "endpoints": [
            {
                "method": e.method,
                "path": e.path,
                "operation_id": e.operation_id,
                "requires_auth": e.requires_auth,
                "statuses": e.status_codes,
                "parameters": [
                    {"name": p.name, "in": p.location, "required": p.required}
                    for p in e.parameters
                ],
                "has_body": e.request_body is not None,
            }
            for e in spec.endpoints
        ],
    }
