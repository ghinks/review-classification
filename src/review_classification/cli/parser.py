"""GitHub repository parser for various input formats."""

import re
from dataclasses import dataclass


@dataclass
class GitHubRepo:
    """Represents a GitHub repository with owner and name."""

    owner: str
    name: str

    @classmethod
    def from_string(cls, repo_input: str) -> "GitHubRepo":
        """Parse various GitHub repo formats.

        Supports:
        - owner/repo
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git

        Args:
            repo_input: Repository identifier in various formats

        Returns:
            GitHubRepo instance

        Raises:
            ValueError: If the repository format is invalid
        """
        # Remove .git suffix if present
        repo_input = repo_input.removesuffix(".git")

        # GitHub URL patterns
        https_pattern = r"https?://github\.com/([^/]+)/([^/]+)"
        ssh_pattern = r"git@github\.com:([^/]+)/([^/]+)"

        if (match := re.match(https_pattern, repo_input)) or (
            match := re.match(ssh_pattern, repo_input)
        ):
            return cls(owner=match.group(1), name=match.group(2))
        elif "/" in repo_input:
            owner, name = repo_input.split("/", 1)
            return cls(owner=owner.strip(), name=name.strip())
        else:
            raise ValueError(
                f"Invalid repository format: {repo_input}\n"
                "Expected: owner/repo or GitHub URL"
            )
