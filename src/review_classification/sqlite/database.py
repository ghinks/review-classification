from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session, SQLModel, col, create_engine, delete, select

from .models import PRFeatures, PROutlierScore, PullRequest

# Use a local file database
sqlite_file_name = "review_classification.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)


def init_db() -> None:
    """Initialize the database tables."""
    SQLModel.metadata.create_all(engine)
    # Migrate: add base_branch column to existing databases that predate it
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE pullrequest ADD COLUMN base_branch TEXT"))
            conn.commit()
        except Exception:
            pass  # Column already exists


def get_session() -> Session:
    """Return a new database session."""
    return Session(engine)


def save_pr(pr_data: PullRequest) -> PullRequest:
    """Save or update a Pull Request in the database.

    If a PR with the same number AND repository_name exists, it is updated.
    """
    with Session(engine) as session:
        statement = select(PullRequest).where(
            PullRequest.number == pr_data.number,
            PullRequest.repository_name == pr_data.repository_name,
        )
        results = session.exec(statement)
        existing_pr = results.first()

        if existing_pr:
            # Update existing fields
            existing_pr.title = pr_data.title
            existing_pr.author = pr_data.author
            existing_pr.merged_at = pr_data.merged_at
            existing_pr.closed_at = pr_data.closed_at
            existing_pr.additions = pr_data.additions
            existing_pr.deletions = pr_data.deletions
            existing_pr.changed_files = pr_data.changed_files
            existing_pr.comments = pr_data.comments
            existing_pr.review_comments = pr_data.review_comments
            existing_pr.state = pr_data.state
            existing_pr.url = pr_data.url
            existing_pr.base_branch = pr_data.base_branch
            # repository_name is already correct

            session.add(existing_pr)
            session.commit()
            session.refresh(existing_pr)
            return existing_pr
        else:
            # Create new
            session.add(pr_data)
            session.commit()
            session.refresh(pr_data)
            return pr_data


def save_prs_bulk(prs_data: list[PullRequest], batch_size: int = 500) -> None:
    """Save or update multiple Pull Requests in the database in batches."""
    if not prs_data:
        return

    for i in range(0, len(prs_data), batch_size):
        batch = prs_data[i : i + batch_size]
        with Session(engine) as session:
            # Gather unique repo names and PR numbers in this batch
            repos = {pr.repository_name for pr in batch}
            numbers = [pr.number for pr in batch]

            # Fetch existing PRs in this batch to update them
            statement = select(PullRequest).where(
                col(PullRequest.repository_name).in_(list(repos)),
                col(PullRequest.number).in_(numbers),
            )
            existing_prs = {
                (pr.repository_name, pr.number): pr
                for pr in session.exec(statement).all()
            }

            for pr_data in batch:
                key = (pr_data.repository_name, pr_data.number)
                if key in existing_prs:
                    existing_pr = existing_prs[key]
                    existing_pr.title = pr_data.title
                    existing_pr.author = pr_data.author
                    existing_pr.merged_at = pr_data.merged_at
                    existing_pr.closed_at = pr_data.closed_at
                    existing_pr.additions = pr_data.additions
                    existing_pr.deletions = pr_data.deletions
                    existing_pr.changed_files = pr_data.changed_files
                    existing_pr.comments = pr_data.comments
                    existing_pr.review_comments = pr_data.review_comments
                    existing_pr.state = pr_data.state
                    existing_pr.url = pr_data.url
                    existing_pr.base_branch = pr_data.base_branch
                    session.add(existing_pr)
                else:
                    session.add(pr_data)
                    # Add to existing_prs to handle potential duplicates
                    # in the same batch
                    existing_prs[key] = pr_data

            session.commit()


def delete_all_prs() -> None:
    """Delete all Pull Request records from the database."""
    with Session(engine) as session:
        statement = delete(PullRequest)
        session.exec(statement)
        session.commit()


def save_pr_features(features: PRFeatures) -> PRFeatures:
    """Save or update PR features in the database.

    If features for the same pull_request_id exist, they are updated.
    """
    with Session(engine) as session:
        statement = select(PRFeatures).where(
            PRFeatures.pull_request_id == features.pull_request_id
        )
        existing = session.exec(statement).first()

        if existing:
            # Update existing
            for key, value in features.model_dump(exclude={"id"}).items():
                setattr(existing, key, value)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # Create new
            session.add(features)
            session.commit()
            session.refresh(features)
            return features


def save_pr_features_bulk(
    session: Session, features_list: list[PRFeatures], batch_size: int = 500
) -> None:
    """Save or update multiple PR features in the database using an active session."""
    if not features_list:
        return

    for i in range(0, len(features_list), batch_size):
        batch = features_list[i : i + batch_size]
        pr_ids = [f.pull_request_id for f in batch]

        # Fetch existing features for these PR IDs
        statement = select(PRFeatures).where(
            col(PRFeatures.pull_request_id).in_(pr_ids)
        )
        existing_features = {
            f.pull_request_id: f for f in session.exec(statement).all()
        }

        for f in batch:
            if f.pull_request_id in existing_features:
                existing = existing_features[f.pull_request_id]
                for key, value in f.model_dump(exclude={"id"}).items():
                    setattr(existing, key, value)
                session.add(existing)
            else:
                session.add(f)
                # Keep track to handle potential duplicates in the batch
                existing_features[f.pull_request_id] = f

        session.commit()


def get_pr_features(pr_id: int) -> PRFeatures | None:
    """Get features for a specific PR.

    Args:
        pr_id: The PullRequest id

    Returns:
        PRFeatures if found, None otherwise
    """
    with Session(engine) as session:
        statement = select(PRFeatures).where(PRFeatures.pull_request_id == pr_id)
        return session.exec(statement).first()


def get_repos_for_org(org_name: str) -> list[str]:
    """Return distinct repository names stored in the DB for the given org/owner.

    Avoids any network call — resolves org repos entirely from fetched data.
    """
    with Session(engine) as session:
        statement = (
            select(col(PullRequest.repository_name))
            .where(col(PullRequest.repository_name).like(f"{org_name}/%"))
            .distinct()
        )
        return sorted(session.exec(statement).all())


def get_outlier_scores(
    repository_name: str, outliers_only: bool = True
) -> list[PROutlierScore]:
    """Get outlier scores for a repository.

    Args:
        repository_name: Repository to query
        outliers_only: If True, only return PRs flagged as outliers

    Returns:
        List of PROutlierScore ordered by max_abs_z_score descending
    """
    with Session(engine) as session:
        statement = select(PROutlierScore).where(
            PROutlierScore.repository_name == repository_name
        )

        if outliers_only:
            statement = statement.where(PROutlierScore.is_outlier == True)  # noqa: E712

        statement = statement.order_by(
            PROutlierScore.max_abs_z_score.desc()  # type: ignore[union-attr]
        )

        return list(session.exec(statement).all())


def get_latest_pr_date(repository_name: str) -> datetime | None:
    """Get the latest created_at date for a PR in the repository.

    Args:
        repository_name: The name of the repository (e.g., owner/repo).

    Returns:
        The latest created_at datetime or None if no PRs are found or table is missing.
    """
    from sqlalchemy.exc import OperationalError

    try:
        with Session(engine) as session:
            statement = (
                select(col(PullRequest.created_at))
                .where(PullRequest.repository_name == repository_name)
                .order_by(col(PullRequest.created_at).desc())
            )
            return session.exec(statement).first()
    except OperationalError:
        return None
