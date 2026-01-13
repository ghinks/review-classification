from datetime import UTC, datetime

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


class PRFeatures(SQLModel, table=True):
    """Computed features for PR analysis."""

    __tablename__ = "prfeatures"
    __table_args__ = (UniqueConstraint("pull_request_id"),)

    id: int | None = Field(default=None, primary_key=True)
    pull_request_id: int = Field(foreign_key="pullrequest.id", index=True)

    # Engineered features
    review_duration_hours: float | None = None
    code_churn: int = 0
    comment_density_per_file: float | None = None
    comment_density_per_line: float | None = None
    total_comments: int = 0

    # Timestamp
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PROutlierScore(SQLModel, table=True):
    """Z-scores and outlier flags for PR analysis."""

    __tablename__ = "proutlierscore"
    __table_args__ = (UniqueConstraint("pull_request_id"),)

    id: int | None = Field(default=None, primary_key=True)
    pull_request_id: int = Field(foreign_key="pullrequest.id", index=True)
    repository_name: str = Field(index=True)

    # Z-scores for raw metrics
    z_additions: float | None = None
    z_deletions: float | None = None
    z_changed_files: float | None = None
    z_comments: float | None = None
    z_review_comments: float | None = None

    # Z-scores for engineered features
    z_review_duration: float | None = None
    z_code_churn: float | None = None
    z_comment_density_per_file: float | None = None
    z_comment_density_per_line: float | None = None

    # Outlier flags
    is_outlier: bool = False
    outlier_features: str | None = None  # JSON array of feature names
    max_abs_z_score: float | None = None

    # Metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sample_size: int = 0
