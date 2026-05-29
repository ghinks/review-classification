"""Tests for fetch command behavior."""

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
import typer

cli_app = import_module("review_classification.cli.app")


def _org_repos(_org_name: str) -> list[str]:
    return ["my-org/existing", "my-org/new"]


def _save_pr(_pr: Any) -> None:
    return None


def _no_latest_pr_date(_repo_name: str) -> None:
    return None


def test_incremental_org_fetch_skips_repo_without_existing_data(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Org incremental fetches skip newly discovered repos without DB history."""
    fetched_repos: list[str] = []

    def latest_pr_date(repo_name: str) -> datetime | None:
        if repo_name == "my-org/existing":
            return datetime(2024, 1, 15, tzinfo=UTC)
        return None

    def fetch_prs(
        repo_name: str,
        start_date: str | None = None,
        end_date: str | None = None,
        token: str | None = None,
    ) -> list[Any]:
        del start_date, end_date, token
        fetched_repos.append(repo_name)
        return []

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        "review_classification.queries.github_client.get_org_repos", _org_repos
    )
    monkeypatch.setattr(
        "review_classification.sqlite.database.get_latest_pr_date", latest_pr_date
    )
    monkeypatch.setattr(
        "review_classification.queries.github_client.fetch_prs", fetch_prs
    )
    monkeypatch.setattr("review_classification.sqlite.database.init_db", lambda: None)
    monkeypatch.setattr("review_classification.sqlite.database.save_pr", _save_pr)

    cli_app.fetch(
        repo=None,
        org=["my-org"],
        config=None,
        collate_start=None,
        collate_end=None,
        reset_db=False,
        verbose=False,
        incremental=True,
    )

    captured = capsys.readouterr()
    assert fetched_repos == ["my-org/existing"]
    assert (
        "Skipping my-org/new: no existing PR data found for incremental fetch."
        in captured.err
    )


def test_incremental_repo_fetch_still_errors_without_existing_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Explicit repo incremental fetches still require existing DB history."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "review_classification.sqlite.database.get_latest_pr_date", _no_latest_pr_date
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_app.fetch(
            repo=["my-org/new"],
            org=None,
            config=None,
            collate_start=None,
            collate_end=None,
            reset_db=False,
            verbose=False,
            incremental=True,
        )

    assert exc_info.value.exit_code == 1
