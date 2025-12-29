"""Main entry point for review-classification CLI."""

from .cli import app


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
