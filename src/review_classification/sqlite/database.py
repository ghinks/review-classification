from sqlmodel import Session, SQLModel, create_engine, delete, select

from .models import PullRequest

# Use a local file database
sqlite_file_name = "review_classification.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)


def init_db() -> None:
    """Initialize the database tables."""
    SQLModel.metadata.create_all(engine)


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


def delete_all_prs() -> None:
    """Delete all Pull Request records from the database."""
    with Session(engine) as session:
        statement = delete(PullRequest)
        session.exec(statement)
        session.commit()
