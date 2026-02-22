"""Tests for the multi-repository TOML config parser."""

import pytest

from review_classification.cli.config import (
    MultiRepoConfig,
    RepoConfig,
    parse_config_file,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toml(tmp_path, content: str):
    """Write a TOML file and return its Path."""
    p = tmp_path / "repos.toml"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# parse_config_file – happy paths
# ---------------------------------------------------------------------------


def test_minimal_config(tmp_path) -> None:
    """A config with only a repository name is valid."""
    cfg_path = _write_toml(
        tmp_path,
        """
[[repositories]]
name = "owner/repo"
""",
    )
    cfg = parse_config_file(cfg_path)
    assert len(cfg.repositories) == 1
    assert cfg.repositories[0].name == "owner/repo"


def test_multiple_repositories(tmp_path) -> None:
    """Multiple [[repositories]] entries are all parsed."""
    cfg_path = _write_toml(
        tmp_path,
        """
[[repositories]]
name = "owner/repo-a"

[[repositories]]
name = "owner/repo-b"
""",
    )
    cfg = parse_config_file(cfg_path)
    assert len(cfg.repositories) == 2
    assert cfg.repositories[0].name == "owner/repo-a"
    assert cfg.repositories[1].name == "owner/repo-b"


def test_global_defaults_parsed(tmp_path) -> None:
    """[defaults] values are read into MultiRepoConfig."""
    cfg_path = _write_toml(
        tmp_path,
        """
[defaults]
start = "2024-01-01"
end   = "2024-12-31"
threshold   = 1.5
min_samples = 20
classify_start = "2024-01-01"
classify_end   = "2024-06-30"

[[repositories]]
name = "owner/repo"
""",
    )
    cfg = parse_config_file(cfg_path)
    assert cfg.start == "2024-01-01"
    assert cfg.end == "2024-12-31"
    assert cfg.threshold == 1.5
    assert cfg.min_samples == 20
    assert cfg.classify_start == "2024-01-01"
    assert cfg.classify_end == "2024-06-30"


def test_per_repo_overrides_parsed(tmp_path) -> None:
    """Per-repository fields are stored on the RepoConfig."""
    cfg_path = _write_toml(
        tmp_path,
        """
[defaults]
start = "2024-01-01"
threshold = 2.0

[[repositories]]
name        = "owner/repo"
start       = "2024-06-01"
threshold   = 3.0
min_samples = 50
""",
    )
    cfg = parse_config_file(cfg_path)
    repo = cfg.repositories[0]
    assert repo.start == "2024-06-01"
    assert repo.threshold == 3.0
    assert repo.min_samples == 50


# ---------------------------------------------------------------------------
# MultiRepoConfig.resolve – default propagation
# ---------------------------------------------------------------------------


def test_resolve_applies_global_defaults() -> None:
    """resolve() fills in global defaults for unset repo fields."""
    multi = MultiRepoConfig(
        start="2024-01-01",
        end="2024-12-31",
        threshold=1.5,
        min_samples=20,
        classify_start="2024-01-01",
        classify_end="2024-06-30",
    )
    repo = RepoConfig(name="owner/repo")
    resolved = multi.resolve(repo)

    assert resolved.name == "owner/repo"
    assert resolved.start == "2024-01-01"
    assert resolved.end == "2024-12-31"
    assert resolved.threshold == 1.5
    assert resolved.min_samples == 20
    assert resolved.classify_start == "2024-01-01"
    assert resolved.classify_end == "2024-06-30"


def test_resolve_repo_value_takes_precedence() -> None:
    """Per-repository values override global defaults during resolve()."""
    multi = MultiRepoConfig(start="2024-01-01", threshold=2.0, min_samples=30)
    repo = RepoConfig(name="owner/repo", start="2024-06-01", threshold=3.5)
    resolved = multi.resolve(repo)

    assert resolved.start == "2024-06-01"
    assert resolved.threshold == 3.5
    # min_samples was not set on the repo – global default applies
    assert resolved.min_samples == 30


def test_resolve_none_global_not_overridden_by_repo_value() -> None:
    """When the global default is None and the repo sets a value, repo wins."""
    multi = MultiRepoConfig()  # start=None by default
    repo = RepoConfig(name="owner/repo", start="2024-03-01")
    resolved = multi.resolve(repo)
    assert resolved.start == "2024-03-01"


def test_resolve_both_none_stays_none() -> None:
    """When neither global nor repo sets a field, resolved value is None."""
    multi = MultiRepoConfig()
    repo = RepoConfig(name="owner/repo")
    resolved = multi.resolve(repo)
    assert resolved.start is None
    assert resolved.classify_start is None


# ---------------------------------------------------------------------------
# parse_config_file – error cases
# ---------------------------------------------------------------------------


def test_missing_file_raises_file_not_found(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        parse_config_file(tmp_path / "nonexistent.toml")


def test_invalid_toml_raises_value_error(tmp_path) -> None:
    cfg_path = _write_toml(tmp_path, "this is not [ valid toml !!!")
    with pytest.raises(ValueError, match="Invalid TOML"):
        parse_config_file(cfg_path)


def test_empty_repositories_raises_value_error(tmp_path) -> None:
    """A config with no [[repositories]] entries is rejected."""
    cfg_path = _write_toml(
        tmp_path,
        """
[defaults]
start = "2024-01-01"
""",
    )
    with pytest.raises(ValueError, match="at least one repository"):
        parse_config_file(cfg_path)


def test_repository_missing_name_raises_value_error(tmp_path) -> None:
    """A [[repositories]] entry without a 'name' field is rejected."""
    cfg_path = _write_toml(
        tmp_path,
        """
[[repositories]]
start = "2024-01-01"
""",
    )
    with pytest.raises(ValueError, match="missing the required 'name' field"):
        parse_config_file(cfg_path)


def test_invalid_threshold_type_raises_value_error(tmp_path) -> None:
    """A non-numeric threshold value is rejected."""
    cfg_path = _write_toml(
        tmp_path,
        """
[[repositories]]
name      = "owner/repo"
threshold = "not-a-number"
""",
    )
    with pytest.raises(ValueError):
        parse_config_file(cfg_path)
