"""Turn a resolved OpenAPI 3.x document into QAgent's own models."""

from __future__ import annotations

from typing import Any, cast

from qagent.models import (
    METHOD_ORDER,
    ApiSpec,
    Endpoint,
    HttpMethod,
    Parameter,
    ParameterLocation,
    RequestBody,
    ResponseSpec,
)

_METHODS: tuple[str, ...] = tuple(m.lower() for m in METHOD_ORDER)
_LOCATIONS: frozenset[str] = frozenset({"path", "query", "header", "cookie"})


def parse_document(document: dict[str, Any]) -> ApiSpec:
    """Build an :class:`ApiSpec` from a document whose ``$ref``s are already resolved."""
    info = document.get("info") or {}
    components = document.get("components") or {}
    global_security = _parse_security(document.get("security"))

    endpoints: list[Endpoint] = []
    for path, path_item in (document.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        path_params = _parse_parameters(path_item.get("parameters"))
        for method in _METHODS:
            operation = path_item.get(method)
            if isinstance(operation, dict):
                endpoints.append(
                    _parse_operation(str(path), method, operation, path_params, global_security)
                )

    endpoints.sort(key=lambda e: (e.path, METHOD_ORDER.index(e.method)))

    return ApiSpec(
        title=str(info.get("title", "Untitled API")),
        version=str(info.get("version", "")),
        openapi_version=str(document.get("openapi", "")),
        description=info.get("description"),
        servers=[
            str(s["url"])
            for s in document.get("servers") or []
            if isinstance(s, dict) and "url" in s
        ],
        security_schemes=dict(components.get("securitySchemes") or {}),
        endpoints=endpoints,
    )


def _parse_operation(
    path: str,
    method: str,
    operation: dict[str, Any],
    path_params: list[Parameter],
    global_security: list[dict[str, list[str]]],
) -> Endpoint:
    # Operation-level parameters override path-level ones with the same name + location.
    merged: dict[tuple[str, str], Parameter] = {(p.name, p.location): p for p in path_params}
    for param in _parse_parameters(operation.get("parameters")):
        merged[(param.name, param.location)] = param

    # `security: []` on an operation explicitly makes it public, so check for the
    # key rather than truthiness.
    security = (
        _parse_security(operation["security"]) if "security" in operation else global_security
    )

    return Endpoint(
        method=cast(HttpMethod, method.upper()),
        path=path,
        operation_id=operation.get("operationId"),
        summary=operation.get("summary"),
        description=operation.get("description"),
        tags=[str(t) for t in operation.get("tags") or []],
        parameters=list(merged.values()),
        request_body=_parse_request_body(operation.get("requestBody")),
        responses={
            str(status): _parse_response(str(status), response)
            for status, response in (operation.get("responses") or {}).items()
            if isinstance(response, dict)
        },
        security=security,
        deprecated=bool(operation.get("deprecated", False)),
    )


def _parse_parameters(raw: Any) -> list[Parameter]:
    params: list[Parameter] = []
    for item in raw or []:
        if not isinstance(item, dict) or "name" not in item:
            continue
        location = item.get("in")
        if location not in _LOCATIONS:
            continue
        schema = item.get("schema")
        if schema is None:
            # OpenAPI also allows `content: {media-type: {schema}}` for complex params.
            schema = next(iter(_parse_content(item.get("content")).values()), {})
        params.append(
            Parameter(
                name=str(item["name"]),
                location=cast(ParameterLocation, location),
                # Path parameters are always required, whatever the spec says.
                required=location == "path" or bool(item.get("required", False)),
                schema=schema,
                description=item.get("description"),
            )
        )
    return params


def _parse_request_body(raw: Any) -> RequestBody | None:
    if not isinstance(raw, dict):
        return None
    return RequestBody(
        required=bool(raw.get("required", False)),
        content=_parse_content(raw.get("content")),
        description=raw.get("description"),
    )


def _parse_response(status: str, raw: dict[str, Any]) -> ResponseSpec:
    return ResponseSpec(
        status=status,
        description=raw.get("description"),
        content=_parse_content(raw.get("content")),
    )


def _parse_content(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(media_type): dict(media.get("schema") or {})
        for media_type, media in raw.items()
        if isinstance(media, dict)
    }


def _parse_security(raw: Any) -> list[dict[str, list[str]]]:
    if not isinstance(raw, list):
        return []
    return [
        {str(name): [str(scope) for scope in scopes or []] for name, scopes in req.items()}
        for req in raw
        if isinstance(req, dict)
    ]
