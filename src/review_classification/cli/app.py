"""Typer CLI application for review-classification."""

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

        if verbose:
            typer.echo(f"Repository: {repo.owner}/{repo.name}")
            if start_date:
                typer.echo(f"Start date: {start_date}")
            if end_date:
                typer.echo(f"End date: {end_date}")

        typer.echo(f"Analyzing {repo.owner}/{repo.name}...")

        # TODO: Implement PR analysis logic
        typer.echo("Analysis not yet implemented - coming soon!")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
