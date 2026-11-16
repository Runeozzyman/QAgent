from __future__ import annotations

import http.server
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from qagent.spec.errors import SpecLoadError
from qagent.spec.loader import is_url, load_document, parse_text


def test_loads_yaml_file(petstore_path: Path) -> None:
    doc = load_document(petstore_path)
    assert doc["info"]["title"] == "Petstore"


def test_loads_json_file(minibank_path: Path) -> None:
    doc = load_document(str(minibank_path))
    assert doc["openapi"] == "3.1.0"


def test_missing_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(SpecLoadError, match="not found"):
        load_document(tmp_path / "nope.yaml")


def test_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SpecLoadError, match="directory"):
        load_document(tmp_path)


def test_empty_text_is_rejected() -> None:
    with pytest.raises(SpecLoadError, match="empty"):
        parse_text("   \n")


def test_bad_yaml_reports_line() -> None:
    with pytest.raises(SpecLoadError, match=r"line \d+"):
        parse_text("openapi: 3.0.0\ninfo: [unclosed\n")


def test_bad_json_reports_line() -> None:
    with pytest.raises(SpecLoadError, match="not valid JSON"):
        parse_text('{"openapi": }')


def test_top_level_must_be_object() -> None:
    with pytest.raises(SpecLoadError, match="top level"):
        parse_text("- just\n- a list\n")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("http://localhost:8000/openapi.json", True),
        ("https://example.com/spec.yaml", True),
        ("specs/openapi.yaml", False),
        ("/abs/path.json", False),
    ],
)
def test_is_url(source: str, expected: bool) -> None:
    assert is_url(source) is expected


@pytest.fixture
def spec_server(petstore_path: Path) -> Iterator[str]:
    """Serve the fixtures folder over HTTP on a random local port."""
    directory = str(petstore_path.parent)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_loads_from_url(spec_server: str) -> None:
    doc = load_document(f"{spec_server}/petstore.yaml")
    assert doc["info"]["title"] == "Petstore"


def test_http_error_is_reported(spec_server: str) -> None:
    with pytest.raises(SpecLoadError, match="HTTP 404"):
        load_document(f"{spec_server}/missing.json")


def test_unreachable_url_is_reported() -> None:
    # Port 9 (discard) is essentially never listening locally.
    with pytest.raises(SpecLoadError, match="Could not reach"):
        load_document("http://127.0.0.1:9/openapi.json", timeout=2)
