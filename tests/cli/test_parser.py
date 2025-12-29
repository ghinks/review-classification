"""Tests for GitHub repository parser."""

import pytest
from review_classification.cli.parser import GitHubRepo


def test_parse_owner_slash_repo() -> None:
    """Test parsing owner/repo format."""
    repo = GitHubRepo.from_string("owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_https_url() -> None:
    """Test parsing HTTPS GitHub URL."""
    repo = GitHubRepo.from_string("https://github.com/owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_https_url_with_git_suffix() -> None:
    """Test parsing HTTPS URL with .git suffix."""
    repo = GitHubRepo.from_string("https://github.com/owner/repo.git")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_http_url() -> None:
    """Test parsing HTTP GitHub URL."""
    repo = GitHubRepo.from_string("http://github.com/owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_ssh_url() -> None:
    """Test parsing SSH GitHub URL."""
    repo = GitHubRepo.from_string("git@github.com:owner/repo")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_ssh_url_with_git_suffix() -> None:
    """Test parsing SSH URL with .git suffix."""
    repo = GitHubRepo.from_string("git@github.com:owner/repo.git")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_with_whitespace() -> None:
    """Test parsing with surrounding whitespace."""
    repo = GitHubRepo.from_string(" owner / repo ")
    assert repo.owner == "owner"
    assert repo.name == "repo"


def test_parse_invalid_format() -> None:
    """Test that invalid format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid repository format"):
        GitHubRepo.from_string("invalid")


def test_parse_invalid_format_error_message() -> None:
    """Test that error message is helpful."""
    with pytest.raises(ValueError) as exc_info:
        GitHubRepo.from_string("justareponame")

    assert "Expected: owner/repo or GitHub URL" in str(exc_info.value)
