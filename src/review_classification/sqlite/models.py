from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class PullRequest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("repository_name", "number"),)

    id: int | None = Field(default=None, primary_key=True)
    repository_name: str = Field(index=True)
    number: int = Field(index=True)
    title: str
    author: str = Field(index=True)
    created_at: datetime
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    comments: int = 0
    review_comments: int = 0
    state: str
    url: str
