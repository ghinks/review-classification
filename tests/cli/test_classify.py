"""Tests for classify command behavior."""

from importlib import import_module
from pathlib import Path

import pytest
import typer

cli_app = import_module("review_classification.cli.app")


def test_classify_missing_database_shows_clean_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """classify in a dir with no DB exits 1 with a clean message, no traceback."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit) as exc_info:
        cli_app.classify(
            repo=["my-org/repo"],
            org=None,
            config=None,
            threshold=2.0,
            min_samples=30,
            output_format="table",
            verbose=False,
            start=None,
            end=None,
            exclude_primary_merged=False,
        )

    assert exc_info.value.exit_code == 1

    captured = capsys.readouterr()
    assert "No database found" in captured.err
    assert "fetch" in captured.err
    # The raw SQLAlchemy error must never reach the user.
    assert "OperationalError" not in captured.err
    assert "no such table" not in captured.err
    # No stray empty database file should be created.
    assert not (tmp_path / "review_classification.db").exists()


def test_classify_missing_database_for_org_shows_clean_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The org path (which reads the DB to resolve repos) also fails gracefully."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit) as exc_info:
        cli_app.classify(
            repo=None,
            org=["my-org"],
            config=None,
            threshold=2.0,
            min_samples=30,
            output_format="table",
            verbose=False,
            start=None,
            end=None,
            exclude_primary_merged=False,
        )

    assert exc_info.value.exit_code == 1

    captured = capsys.readouterr()
    assert "No database found" in captured.err
    assert "OperationalError" not in captured.err
