from __future__ import annotations

import json
from pathlib import Path

import pytest

typer_testing = pytest.importorskip("typer.testing")
pytest.importorskip("openapi_spec_validator")

from qagent import __version__  # noqa: E402
from qagent.cli import app  # noqa: E402

runner = typer_testing.CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_scan_prints_table(petstore_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(petstore_path)])
    assert result.exit_code == 0, result.output
    assert "Petstore" in result.stdout
    assert "4 endpoints" in result.stdout
    assert "/pets/{petId}" in result.stdout
    assert "[deprecated]" in result.stdout


def test_scan_json(minibank_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(minibank_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["title"] == "Mini Bank"
    assert data["endpoint_count"] == 4


def test_scan_missing_file_exits_1(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 1
    assert "not found" in result.output
