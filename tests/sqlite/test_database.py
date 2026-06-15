"""Tests for sqlite.database helper functions."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from review_classification.sqlite.models import PullRequest


def _make_pr(repo_name: str, number: int) -> PullRequest:
    return PullRequest(
        repository_name=repo_name,
        number=number,
        title=f"PR {number}",
        author="user",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=datetime(2024, 1, 2, tzinfo=UTC),
        additions=10,
        deletions=5,
        changed_files=1,
        comments=0,
        review_comments=0,
        state="closed",
        url=f"http://test.com/{number}",
    )


@pytest.fixture()
def patched_engine(monkeypatch: pytest.MonkeyPatch) -> Engine:
    """Replace the module-level engine with an in-memory SQLite engine."""
    import review_classification.sqlite.database as db_module

    test_engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(test_engine)
    monkeypatch.setattr(db_module, "engine", test_engine)
    return test_engine


def test_get_repos_for_org_returns_correct_repos(patched_engine: Engine) -> None:
    """get_repos_for_org returns only repos belonging to the requested org."""
    from review_classification.sqlite.database import get_repos_for_org

    with Session(patched_engine) as session:
        session.add(_make_pr("my-org/repo-a", 1))
        session.add(_make_pr("my-org/repo-b", 2))
        session.add(_make_pr("other-org/repo-c", 3))
        session.commit()

    result = get_repos_for_org("my-org")
    assert result == ["my-org/repo-a", "my-org/repo-b"]


def test_get_repos_for_org_no_prefix_collision(patched_engine: Engine) -> None:
    """org name prefix must be followed by '/' — no false matches for similar names."""
    from review_classification.sqlite.database import get_repos_for_org

    with Session(patched_engine) as session:
        session.add(_make_pr("my-org/repo-a", 1))
        session.add(_make_pr("my-org-extra/repo-b", 2))
        session.commit()

    assert get_repos_for_org("my-org") == ["my-org/repo-a"]
    assert get_repos_for_org("my-org-extra") == ["my-org-extra/repo-b"]


def test_get_repos_for_org_empty_when_no_data(patched_engine: Engine) -> None:  # noqa: ARG001
    """Returns an empty list when no PRs have been fetched for the org."""
    from review_classification.sqlite.database import get_repos_for_org

    assert get_repos_for_org("unknown-org") == []


def test_get_repos_for_org_deduplicates(patched_engine: Engine) -> None:
    """Multiple PRs from the same repo are collapsed to one entry."""
    from review_classification.sqlite.database import get_repos_for_org

    with Session(patched_engine) as session:
        session.add(_make_pr("my-org/repo-a", 1))
        session.add(_make_pr("my-org/repo-a", 2))
        session.add(_make_pr("my-org/repo-a", 3))
        session.commit()

    assert get_repos_for_org("my-org") == ["my-org/repo-a"]


def test_get_repos_for_org_handles_missing_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns [] instead of raising when the database has no tables yet."""
    import review_classification.sqlite.database as db_module

    # Engine pointing at an in-memory DB with no tables created.
    empty_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", empty_engine)

    assert db_module.get_repos_for_org("any-org") == []


def test_database_is_initialized_false_when_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No database file on disk → not initialized (and no file is created)."""
    import review_classification.sqlite.database as db_module

    monkeypatch.chdir(tmp_path)
    assert db_module.database_is_initialized() is False
    # The check must not lazily create an empty database file.
    assert not (tmp_path / db_module.sqlite_file_name).exists()


def test_database_is_initialized_false_for_empty_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bare file with no tables (failed earlier run) counts as not initialized."""
    import review_classification.sqlite.database as db_module

    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / db_module.sqlite_file_name
    db_path.touch()  # empty SQLite file, no tables
    monkeypatch.setattr(db_module, "engine", create_engine(f"sqlite:///{db_path}"))

    assert db_module.database_is_initialized() is False


def test_database_is_initialized_true_with_tables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A file containing the expected tables counts as initialized."""
    import review_classification.sqlite.database as db_module

    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / db_module.sqlite_file_name
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "engine", engine)

    assert db_module.database_is_initialized() is True
