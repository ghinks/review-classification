"""Typer CLI application for review-classification."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import typer

from .parser import GitHubRepo

app = typer.Typer(help="Identify PR review outliers in GitHub repositories")


@app.command()
def classify(
    repository: Annotated[
        str, typer.Argument(help="GitHub repository (owner/repo or URL)")
    ],
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
    """Classify PR review outliers in a GitHub repository.

    Analyzes pull requests merged within the specified date range and identifies
    outliers based on review time, number of reviews, and qualitative metrics.
    """
    try:
        repo = GitHubRepo.from_string(repository)

        if not start_date:
            # Default to 30 days ago
            start_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

        if verbose:
            typer.echo(f"Repository: {repo.owner}/{repo.name}")
            if start_date:
                typer.echo(f"Start date: {start_date}")
            if end_date:
                typer.echo(f"End date: {end_date}")

        typer.echo(f"Analyzing {repo.owner}/{repo.name}...")

        # Initialize DB
        from ..sqlite.database import delete_all_prs, init_db, save_pr

        init_db()

        if reset_db:
            if verbose:
                typer.echo("Resetting database...")
            delete_all_prs()
            typer.echo("Database reset complete.")

        # Fetch PRs
        # Ensure we have a token
        import os

        from ..queries.github_client import fetch_prs

        if not os.getenv("GITHUB_TOKEN"):
            typer.echo(
                "Warning: GITHUB_TOKEN not set. API rate limits will be very low.",
                err=True,
            )

        prs = fetch_prs(f"{repo.owner}/{repo.name}", start_date, end_date)

        # Save to DB
        typer.echo(f"Saving {len(prs)} PRs to database...")
        for pr in prs:
            save_pr(pr)

        typer.echo(f"Successfully saved {len(prs)} PRs.")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def detect_outliers(
    repository: Annotated[
        str, typer.Argument(help="GitHub repository (owner/repo or URL)")
    ],
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
) -> None:
    """Detect PR review outliers using z-score analysis.

    Analyzes merged PRs to identify statistical outliers based on:
    - Raw metrics: additions, deletions, changed_files, comments, review_comments
    - Engineered features: review_duration, code_churn, comment_density

    Requires repository data to be fetched first using the 'classify' command.
    """
    try:
        repo = GitHubRepo.from_string(repository)
        repo_name = f"{repo.owner}/{repo.name}"

        if verbose:
            typer.echo(f"Analyzing outliers for {repo_name}...")
            typer.echo(f"Z-score threshold: {threshold}")
            typer.echo(f"Minimum sample size: {min_samples}")

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
            # Step 1: Compute features for all PRs
            if verbose:
                typer.echo("Computing features...")

            statement = select(PullRequest).where(
                PullRequest.repository_name == repo_name
            )
            prs = list(session.exec(statement).all())

            if len(prs) == 0:
                typer.echo(
                    f"No PRs found for {repo_name}. Run 'classify' command first.",
                    err=True,
                )
                raise typer.Exit(code=1)

            for pr in prs:
                if pr.id is not None:
                    features = create_pr_features(pr)
                    save_pr_features(features)

            if verbose:
                typer.echo(f"Computed features for {len(prs)} PRs")

            # Step 2: Detect outliers
            if verbose:
                typer.echo("Detecting outliers...")

            results = detect_outliers_for_repository(
                session, repo_name, min_samples, threshold
            )

            # Get sample size for metadata
            _, sample_size = calculate_repository_statistics(
                session, repo_name, min_samples
            )

            # Step 3: Save results
            save_outlier_scores(session, repo_name, results, sample_size)

            outliers = [r for r in results if r.is_outlier]

            if verbose:
                typer.echo(
                    f"Found {len(outliers)} outliers out of {len(results)} PRs "
                    f"({len(outliers) / len(results) * 100:.1f}%)"
                )

            # Step 4: Output results
            output = format_outlier_results(results, output_format)  # type: ignore
            typer.echo(output)

        except InsufficientDataError as e:
            typer.echo(f"Error: {e}", err=True)
            typer.echo(
                f"Repository {repo_name} does not have enough merged PRs for analysis.",
                err=True,
            )
            raise typer.Exit(code=1) from e
        finally:
            session.close()

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
