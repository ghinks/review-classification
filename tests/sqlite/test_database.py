"""Tests for sqlite.database helper functions."""

from datetime import UTC, datetime

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


def test_save_prs_bulk(patched_engine: Engine) -> None:
    """save_prs_bulk inserts new PRs and updates existing ones correctly."""
    from sqlmodel import select

    from review_classification.sqlite.database import save_prs_bulk

    # Batch insert
    prs = [
        _make_pr("org/repo", 1),
        _make_pr("org/repo", 2),
    ]
    save_prs_bulk(prs)

    with Session(patched_engine) as session:
        saved = session.exec(select(PullRequest)).all()
        assert len(saved) == 2
        pr1 = next(p for p in saved if p.number == 1)
        assert pr1.title == "PR 1"

    # Batch update and insert mixed
    prs_updated = [
        _make_pr("org/repo", 1),  # Existing
        _make_pr("org/repo", 3),  # New
    ]
    prs_updated[0].title = "Updated Title"
    save_prs_bulk(prs_updated)

    with Session(patched_engine) as session:
        saved = session.exec(select(PullRequest)).all()
        assert len(saved) == 3
        pr1_updated = next(p for p in saved if p.number == 1)
        assert pr1_updated.title == "Updated Title"
        pr3 = next(p for p in saved if p.number == 3)
        assert pr3.title == "PR 3"


def test_save_pr_features_bulk(patched_engine: Engine) -> None:
    """save_pr_features_bulk inserts and updates PRFeatures using the active session."""
    from sqlmodel import select

    from review_classification.sqlite.database import (
        save_pr_features_bulk,
        save_prs_bulk,
    )
    from review_classification.sqlite.models import PRFeatures

    # Insert some PRs to associate features with
    prs = [
        _make_pr("org/repo", 1),
        _make_pr("org/repo", 2),
    ]
    save_prs_bulk(prs)

    with Session(patched_engine) as session:
        db_prs = session.exec(select(PullRequest)).all()
        pr1 = next(p for p in db_prs if p.number == 1)
        pr2 = next(p for p in db_prs if p.number == 2)

        features1 = PRFeatures(pull_request_id=pr1.id, code_churn=100)
        features2 = PRFeatures(pull_request_id=pr2.id, code_churn=200)

        # Batch insert
        save_pr_features_bulk(session, [features1, features2])

        # Verify inserted
        saved = session.exec(select(PRFeatures)).all()
        assert len(saved) == 2
        f1 = next(f for f in saved if f.pull_request_id == pr1.id)
        assert f1.code_churn == 100

        # Batch update
        features1_updated = PRFeatures(pull_request_id=pr1.id, code_churn=150)
        save_pr_features_bulk(session, [features1_updated])

        session.expire_all()
        f1_updated = session.exec(
            select(PRFeatures).where(PRFeatures.pull_request_id == pr1.id)
        ).one()
        assert f1_updated.code_churn == 150
