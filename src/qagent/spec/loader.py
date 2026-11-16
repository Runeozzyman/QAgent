"""Load a spec document from a local file or an http(s) URL."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from qagent.spec.errors import SpecLoadError

DEFAULT_TIMEOUT_SECONDS = 10.0


def is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def load_document(source: str | Path, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Read a JSON or YAML document and return it as a dict.

    ``source`` is a filesystem path or an ``http://`` / ``https://`` URL such as
    ``http://localhost:8000/openapi.json``.
    """
    source_str = str(source)
    if is_url(source_str):
        text = _fetch_url(source_str, timeout)
    else:
        text = _read_file(Path(source_str))
    return parse_text(text, source_str)


def parse_text(text: str, source: str = "<string>") -> dict[str, Any]:
    """Parse JSON or YAML text. JSON is tried first because it is stricter and faster."""
    stripped = text.lstrip()
    if not stripped:
        raise SpecLoadError(f"{source} is empty.")

    data: Any
    if stripped.startswith(("{", "[")):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SpecLoadError(
                f"{source} is not valid JSON (line {exc.lineno}, column {exc.colno}): {exc.msg}"
            ) from exc
    else:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            location = ""
            mark = getattr(exc, "problem_mark", None)
            if mark is not None:
                location = f" (line {mark.line + 1}, column {mark.column + 1})"
            raise SpecLoadError(f"{source} is not valid YAML{location}.") from exc

    if not isinstance(data, dict):
        raise SpecLoadError(
            f"{source} must contain a JSON/YAML object at the top level, "
            f"not {type(data).__name__}."
        )
    return data


def _read_file(path: Path) -> str:
    if not path.exists():
        raise SpecLoadError(f"Spec file not found: {path}")
    if path.is_dir():
        raise SpecLoadError(f"Expected a spec file but got a directory: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecLoadError(f"{path} is not a UTF-8 text file.") from exc
    except OSError as exc:
        raise SpecLoadError(f"Could not read {path}: {exc.strerror or exc}") from exc


def _fetch_url(url: str, timeout: float) -> str:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json, application/yaml, text/yaml, */*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body: bytes = response.read()
            return body.decode(charset)
    except urllib.error.HTTPError as exc:
        raise SpecLoadError(f"Fetching {url} failed with HTTP {exc.code} {exc.reason}.") from exc
    except urllib.error.URLError as exc:
        raise SpecLoadError(
            f"Could not reach {url}: {exc.reason}. Is the API running?"
        ) from exc
    except TimeoutError as exc:
        raise SpecLoadError(f"Timed out after {timeout:g}s fetching {url}.") from exc
