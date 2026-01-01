import os
from datetime import UTC, datetime

from github import Github, GithubException, RateLimitExceededException
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest as GithubPullRequest
from github.Repository import Repository
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..sqlite.models import PullRequest


def _wait_for_rate_limit(_retry_state: RetryCallState) -> float:
    """Wait strategy that checks for Retry-After or X-RateLimit-Reset headers."""
    # This is a basic implementation. Ideally, we would inspect the exception
    # to get the specific reset time from the headers if available.
    # For now, we fallback to a standard wait + check.
    print("Rate limit exceeded. Waiting for reset...")
    # Safe default or could be smarter about checking the specific reset time
    # if we had access to the headers from the exception here.
    # PyGithub's RateLimitExceededException doesn't always expose the
    # headers directly in a convenient way for tenacity's wait callback
    # without some introspection.
    # For simplicity, we'll wait a fixed time or rely on exponential backoff
    # combined with a check.
    return 60.0  # Wait 60 seconds by default on rate limit


@retry(
    retry=retry_if_exception_type(RateLimitExceededException),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
)
def fetch_repo(g: Github, repo_name: str) -> Repository:
    return g.get_repo(repo_name)


@retry(
    retry=retry_if_exception_type((RateLimitExceededException, GithubException)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def fetch_prs_generator(
    repo: Repository, state: str = "all", sort: str = "created", direction: str = "desc"
) -> PaginatedList[GithubPullRequest]:
    """Generator to yield PRs with retry logic."""
    pulls = repo.get_pulls(state=state, sort=sort, direction=direction)
    return pulls


def fetch_prs(
    repo_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    token: str | None = None,
) -> list[PullRequest]:
    """
    Fetch Pull Requests from a GitHub repository within a date range.

    Args:
        repo_name: "owner/repo"
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"
        token: GitHub API token (optional, defaults to env GITHUB_TOKEN)
    """
    if not token:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            # Try getting from gh cli if installed?
            # For now, assume env var or unauthenticated (limited rate)
            pass

    g = Github(token)
    repo = fetch_repo(g, repo_name)

    # Parse dates
    start_dt = (
        datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
        if start_date
        else None
    )
    end_dt = (
        datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=UTC)
        if end_date
        else None
    )

    print(f"Fetching PRs for {repo_name}...")

    # We fetch all and filter client-side because PyGithub search API
    # might be better for dates but get_pulls is more direct for listing.
    # However, get_pulls returns a PaginatedList. iterating it triggers requests.

    prs_data = []

    # Using the generator to handle pagination transparently
    pulls = fetch_prs_generator(
        repo, state="closed"
    )  # Focusing on closed/merged for review analysis usually?
    # Or 'all' if we want open ones too. The prompt said "PR information".
    # Usually review analysis implies completed reviews, so closed/merged is typical,
    # but let's stick to 'all' to be safe, or just iterate.

    # Optimization: If sorted by created desc, we can stop when we go past start_date
    pulls = fetch_prs_generator(repo, state="all", sort="created", direction="desc")

    count = 0

    for pr in pulls:
        created_at = pr.created_at.replace(tzinfo=UTC)

        # Filter by Date
        if end_dt and created_at > end_dt:
            continue

        if start_dt and created_at < start_dt:
            # Since we are sorting by created desc, if we assume strict ordering,
            # we could break here.
            break

        # Convert to our model
        pr_model = PullRequest(
            repository_name=repo_name,
            number=pr.number,
            title=pr.title,
            author=pr.user.login if pr.user else "ghost",
            created_at=created_at,
            merged_at=pr.merged_at.replace(tzinfo=UTC) if pr.merged_at else None,
            closed_at=pr.closed_at.replace(tzinfo=UTC) if pr.closed_at else None,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
            comments=pr.comments,
            review_comments=pr.review_comments,
            state=pr.state,
            url=pr.html_url,
        )
        prs_data.append(pr_model)
        count += 1
        if count % 10 == 0:
            print(f"Fetched {count} PRs...", end="\r")

    print(f"\nTotal PRs fetched: {len(prs_data)}")
    return prs_data
