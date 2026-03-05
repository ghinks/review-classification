"""Typer CLI application for review-classification."""

from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from .config import RepoConfig, parse_config_file
from .parser import GitHubRepo

app = typer.Typer(help="Identify PR review outliers in GitHub repositories")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("review-classification"))
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the package version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    pass


# ---------------------------------------------------------------------------
# Internal helpers – contain the per-repository business logic so that both
# the single-repo and multi-repo code paths share one implementation.
# ---------------------------------------------------------------------------


def _fetch_single(
    repo_name: str,
    start_date: str | None,
    end_date: str | None,
    reset_db: bool,
    verbose: bool,
) -> None:
    """Fetch and store PRs for a single repository."""
    repo = GitHubRepo.from_string(repo_name)

    if not start_date:
        start_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

    if verbose:
        typer.echo(f"Repository: {repo.owner}/{repo.name}")
        if start_date:
            typer.echo(f"Start date: {start_date}")
        if end_date:
            typer.echo(f"End date: {end_date}")

    typer.echo(f"Fetching {repo.owner}/{repo.name}...")

    from ..sqlite.database import delete_all_prs, init_db, save_pr

    init_db()

    if reset_db:
        if verbose:
            typer.echo("Resetting database...")
        delete_all_prs()
        typer.echo("Database reset complete.")

    import os

    from ..queries.github_client import fetch_prs

    if not os.getenv("GITHUB_TOKEN"):
        typer.echo(
            "Warning: GITHUB_TOKEN not set. API rate limits will be very low.",
            err=True,
        )

    prs = fetch_prs(f"{repo.owner}/{repo.name}", start_date, end_date)

    typer.echo(f"Saving {len(prs)} PRs to database...")
    for pr in prs:
        save_pr(pr)

    typer.echo(f"Successfully saved {len(prs)} PRs for {repo.owner}/{repo.name}.")


def _detect_single(
    repo_name: str,
    threshold: float,
    min_samples: int,
    output_format: str,
    verbose: bool,
    classify_start: str | None,
    classify_end: str | None,
) -> None:
    """Run outlier detection for a single repository."""
    repo = GitHubRepo.from_string(repo_name)
    full_name = f"{repo.owner}/{repo.name}"

    classify_start_dt: datetime | None = None
    classify_end_dt: datetime | None = None

    if classify_start:
        classify_start_dt = datetime.strptime(classify_start, "%Y-%m-%d").replace(
            tzinfo=UTC
        )
    if classify_end:
        classify_end_dt = datetime.strptime(classify_end, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=UTC
        )

    if verbose:
        typer.echo(f"Analyzing outliers for {full_name}...")
        typer.echo(f"Z-score threshold: {threshold}")
        typer.echo(f"Minimum sample size: {min_samples}")
        if classify_start_dt or classify_end_dt:
            start_label = classify_start or "unbounded"
            end_label = classify_end or "unbounded"
            typer.echo(f"Classification window: {start_label} to {end_label}")

    from sqlmodel import select

    from ..analysis.outlier_detector import (
        calculate_repository_statistics,
        detect_outliers_for_repository,
        save_outlier_scores,
    )
    from ..analysis.statistics import InsufficientDataError
    from ..features.engineering import create_pr_features
    from ..sqlite.database import get_session, init_db, save_pr_features
    from ..sqlite.models import PullRequest
    from .output import format_outlier_results

    init_db()
    session = get_session()

    try:
        if verbose:
            typer.echo("Computing features...")

        statement = select(PullRequest).where(PullRequest.repository_name == full_name)
        prs = list(session.exec(statement).all())

        if len(prs) == 0:
            typer.echo(
                f"No PRs found for {full_name}. Run 'fetch' command first.",
                err=True,
            )
            raise typer.Exit(code=1)

        for pr in prs:
            if pr.id is not None:
                features = create_pr_features(pr)
                save_pr_features(features)

        if verbose:
            typer.echo(f"Computed features for {len(prs)} PRs")

        if verbose:
            typer.echo("Detecting outliers...")

        results = detect_outliers_for_repository(
            session,
            full_name,
            min_samples,
            threshold,
            classify_start=classify_start_dt,
            classify_end=classify_end_dt,
        )

        _, sample_size = calculate_repository_statistics(
            session,
            full_name,
            min_samples,
            stats_start=classify_start_dt,
            stats_end=classify_end_dt,
        )

        save_outlier_scores(session, full_name, results, sample_size)

        outliers = [r for r in results if r.is_outlier]

        if verbose:
            typer.echo(
                f"Found {len(outliers)} outliers out of {len(results)} PRs "
                f"({len(outliers) / len(results) * 100:.1f}%)"
            )

        output = format_outlier_results(results, output_format)  # type: ignore
        typer.echo(output)

    except InsufficientDataError as e:
        typer.echo(f"Error: {e}", err=True)
        typer.echo(
            f"Repository {full_name} does not have enough merged PRs for analysis.",
            err=True,
        )
        raise typer.Exit(code=1) from e
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def _resolve_targets(
    repos: list[str],
    orgs: list[str],
    config_path: Path | None,
    default_start: str | None = None,
    default_end: str | None = None,
    default_threshold: float | None = None,
    default_min_samples: int | None = None,
    default_classify_start: str | None = None,
    default_classify_end: str | None = None,
) -> list[RepoConfig]:
    """Resolve CLI arguments and config file into a concrete list of repositories."""
    from ..queries.github_client import get_org_repos

    resolved_repos: dict[str, RepoConfig] = {}

    def add_repo(rc: RepoConfig) -> None:
        if rc.name not in resolved_repos:
            resolved_repos[rc.name] = rc
        else:
            # Config file takes precedence if it was added earlier?
            # Actually, let's just keep the first one we see or merge.
            pass

    if config_path:
        multi = parse_config_file(config_path)
        for repo_cfg in multi.repositories:
            add_repo(multi.resolve(repo_cfg))

        for org_cfg in multi.organizations:
            org_repos = get_org_repos(org_cfg.name)
            for r in org_repos:
                if r not in org_cfg.exclude_repos:
                    # Create a RepoConfig inheriting from org_cfg, then global
                    rc = RepoConfig(
                        name=r,
                        start=org_cfg.start
                        if org_cfg.start is not None
                        else multi.start,
                        end=org_cfg.end if org_cfg.end is not None else multi.end,
                        threshold=org_cfg.threshold
                        if org_cfg.threshold is not None
                        else multi.threshold,
                        min_samples=org_cfg.min_samples
                        if org_cfg.min_samples is not None
                        else multi.min_samples,
                        classify_start=org_cfg.classify_start
                        if org_cfg.classify_start is not None
                        else multi.classify_start,
                        classify_end=org_cfg.classify_end
                        if org_cfg.classify_end is not None
                        else multi.classify_end,
                    )
                    add_repo(rc)

    # Add explicit CLI repos
    for r in repos:
        rc = RepoConfig(
            name=r,
            start=default_start,
            end=default_end,
            threshold=default_threshold,
            min_samples=default_min_samples,
            classify_start=default_classify_start,
            classify_end=default_classify_end,
        )
        add_repo(rc)

    # Add explicit CLI orgs
    for o in orgs:
        org_repos = get_org_repos(o)
        for r in org_repos:
            rc = RepoConfig(
                name=r,
                start=default_start,
                end=default_end,
                threshold=default_threshold,
                min_samples=default_min_samples,
                classify_start=default_classify_start,
                classify_end=default_classify_end,
            )
            add_repo(rc)

    return list(resolved_repos.values())


@app.command()
def fetch(
    repo: Annotated[
        list[str] | None,
        typer.Option(
            "--repo",
            "-r",
            help="GitHub repository (owner/repo). Can be specified multiple times.",
        ),
    ] = None,
    org: Annotated[
        list[str] | None,
        typer.Option(
            "--org",
            "-o",
            help=(
                "GitHub org. Fetches all repositories in the org. "
                "Can be specified multiple times."
            ),
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a TOML config file that defines multiple repositories.",
        ),
    ] = None,
    start_date: Annotated[
        str | None,
        typer.Option("--start", "-s", help="Start date for PR range (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option("--end", "-e", help="End date for PR range (YYYY-MM-DD)"),
    ] = None,
    reset_db: Annotated[
        bool,
        typer.Option("--reset-db", help="Delete all existing data before fetching"),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Fetch PR data from GitHub and store it locally.

    Retrieves pull requests merged within the specified date range and saves
    them to a local SQLite database for subsequent outlier analysis.

    Supply --repo, --org, or a --config file.
    """
    repo_list = repo or []
    org_list = org or []

    if not config and not repo_list and not org_list:
        typer.echo(
            "Error: Provide at least one --repo, --org, or a --config file.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        targets = _resolve_targets(
            repos=repo_list,
            orgs=org_list,
            config_path=config,
            default_start=start_date,
            default_end=end_date,
        )

        for target in targets:
            _fetch_single(
                target.name,
                target.start,
                target.end,
                reset_db,
                verbose,
            )

    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def detect_outliers(
    repo: Annotated[
        list[str] | None,
        typer.Option(
            "--repo",
            "-r",
            help="GitHub repository (owner/repo). Can be specified multiple times.",
        ),
    ] = None,
    org: Annotated[
        list[str] | None,
        typer.Option(
            "--org",
            "-o",
            help=(
                "GitHub org. Fetches all repositories in the org. "
                "Can be specified multiple times."
            ),
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a TOML config file that defines multiple repositories.",
        ),
    ] = None,
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="Z-score threshold for outliers"),
    ] = 2.0,
    min_samples: Annotated[
        int,
        typer.Option("--min-samples", help="Minimum number of PRs required"),
    ] = 30,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json, csv"),
    ] = "table",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
    classify_start: Annotated[
        str | None,
        typer.Option(
            "--classify-start",
            help=(
                "Start of the baseline measurement window (YYYY-MM-DD). "
                "PRs after --classify-end are evaluated for outliers."
            ),
        ),
    ] = None,
    classify_end: Annotated[
        str | None,
        typer.Option(
            "--classify-end",
            help=(
                "End of the baseline measurement window (YYYY-MM-DD). "
                "PRs merged after this date are evaluated for outliers."
            ),
        ),
    ] = None,
) -> None:
    """Detect PR review outliers using z-score analysis.

    Analyzes merged PRs to identify statistical outliers based on:
    - Raw metrics: additions, deletions, changed_files, comments, review_comments
    - Engineered features: review_duration, code_churn, comment_density

    Requires repository data to be fetched first using the 'fetch' command.

    Supply --repo, --org, or a --config file.
    Per-repository config from the file takes precedence over CLI flags.
    """
    repo_list = repo or []
    org_list = org or []

    if not config and not repo_list and not org_list:
        typer.echo(
            "Error: Provide at least one --repo, --org, or a --config file.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        targets = _resolve_targets(
            repos=repo_list,
            orgs=org_list,
            config_path=config,
            default_threshold=threshold,
            default_min_samples=min_samples,
            default_classify_start=classify_start,
            default_classify_end=classify_end,
        )

        for target in targets:
            _detect_single(
                target.name,
                target.threshold if target.threshold is not None else threshold,
                target.min_samples if target.min_samples is not None else min_samples,
                output_format,
                verbose,
                target.classify_start,
                target.classify_end,
            )

    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
