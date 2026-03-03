"""Configuration file parser for multi-repository analysis."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoConfig:
    """Configuration for a single repository entry."""

    name: str
    start: str | None = None
    end: str | None = None
    threshold: float | None = None
    min_samples: int | None = None
    classify_start: str | None = None
    classify_end: str | None = None


@dataclass
class OrgConfig:
    """Configuration for a single organization entry."""

    name: str
    start: str | None = None
    end: str | None = None
    threshold: float | None = None
    min_samples: int | None = None
    classify_start: str | None = None
    classify_end: str | None = None
    exclude_repos: list[str] = field(default_factory=list)


@dataclass
class MultiRepoConfig:
    """Top-level configuration for multi-repository analysis.

    Global defaults defined under [defaults] are applied to each repository
    unless the repository provides its own value.
    """

    repositories: list[RepoConfig] = field(default_factory=list)
    organizations: list[OrgConfig] = field(default_factory=list)
    # Global defaults
    start: str | None = None
    end: str | None = None
    threshold: float = 2.0
    min_samples: int = 30
    classify_start: str | None = None
    classify_end: str | None = None

    def resolve(self, repo: RepoConfig) -> RepoConfig:
        """Return a RepoConfig with global defaults applied for unset fields.

        Per-repository values always take precedence over global defaults.

        Args:
            repo: Per-repository configuration (may have unset fields).

        Returns:
            A new RepoConfig with all fields resolved.
        """
        return RepoConfig(
            name=repo.name,
            start=repo.start if repo.start is not None else self.start,
            end=repo.end if repo.end is not None else self.end,
            threshold=repo.threshold if repo.threshold is not None else self.threshold,
            min_samples=(
                repo.min_samples if repo.min_samples is not None else self.min_samples
            ),
            classify_start=(
                repo.classify_start
                if repo.classify_start is not None
                else self.classify_start
            ),
            classify_end=(
                repo.classify_end
                if repo.classify_end is not None
                else self.classify_end
            ),
        )


def parse_config_file(path: Path) -> MultiRepoConfig:
    """Parse a TOML configuration file defining multiple repositories.

    The file must define at least one repository under [[repositories]].
    Global defaults can be set under [defaults] and are applied to any
    repository that does not supply its own value for that field.

    Example config file::

        [defaults]
        start = "2024-01-01"
        end   = "2024-12-31"
        threshold  = 2.0
        min_samples = 30

        [[repositories]]
        name = "owner/repo-a"

        [[repositories]]
        name  = "owner/repo-b"
        start = "2024-06-01"   # overrides [defaults] start

    Args:
        path: Path to the TOML configuration file.

    Returns:
        Populated MultiRepoConfig instance.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file is not valid TOML or fails validation.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Invalid TOML in config file '{path}': {e}") from e

    # --- Parse global defaults ---
    raw_defaults = data.get("defaults", {})
    if not isinstance(raw_defaults, dict):
        raise ValueError("[defaults] must be a TOML table")

    try:
        config = MultiRepoConfig(
            start=_optional_str(raw_defaults, "start"),
            end=_optional_str(raw_defaults, "end"),
            threshold=float(raw_defaults.get("threshold", 2.0)),
            min_samples=int(raw_defaults.get("min_samples", 30)),
            classify_start=_optional_str(raw_defaults, "classify_start"),
            classify_end=_optional_str(raw_defaults, "classify_end"),
        )
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid value in [defaults]: {e}") from e

    # --- Parse repository entries ---
    raw_repos = data.get("repositories", [])
    if not isinstance(raw_repos, list):
        raise ValueError("[[repositories]] must be an array of tables if present")

    for i, raw_repo in enumerate(raw_repos):
        if not isinstance(raw_repo, dict):
            raise ValueError(f"[[repositories]] entry {i} is not a TOML table")
        if "name" not in raw_repo:
            raise ValueError(
                f"[[repositories]] entry {i} is missing the required 'name' field"
            )

        try:
            repo = RepoConfig(
                name=str(raw_repo["name"]),
                start=_optional_str(raw_repo, "start"),
                end=_optional_str(raw_repo, "end"),
                threshold=(
                    float(raw_repo["threshold"]) if "threshold" in raw_repo else None
                ),
                min_samples=(
                    int(raw_repo["min_samples"]) if "min_samples" in raw_repo else None
                ),
                classify_start=_optional_str(raw_repo, "classify_start"),
                classify_end=_optional_str(raw_repo, "classify_end"),
            )
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid value in [[repositories]] entry {i} "
                f"('{raw_repo.get('name', '?')}'): {e}"
            ) from e

        config.repositories.append(repo)

    # --- Parse organization entries ---
    raw_orgs = data.get("organizations", [])
    if not isinstance(raw_orgs, list):
        raise ValueError("[[organizations]] must be an array of tables if present")

    for i, raw_org in enumerate(raw_orgs):
        if not isinstance(raw_org, dict):
            raise ValueError(f"[[organizations]] entry {i} is not a TOML table")
        if "name" not in raw_org:
            raise ValueError(
                f"[[organizations]] entry {i} is missing the required 'name' field"
            )

        try:
            exclude = raw_org.get("exclude_repos", [])
            if not isinstance(exclude, list):
                if isinstance(exclude, str):
                    exclude = [exclude]
                else:
                    raise ValueError("'exclude_repos' must be a list of strings")

            org = OrgConfig(
                name=str(raw_org["name"]),
                start=_optional_str(raw_org, "start"),
                end=_optional_str(raw_org, "end"),
                threshold=(
                    float(raw_org["threshold"]) if "threshold" in raw_org else None
                ),
                min_samples=(
                    int(raw_org["min_samples"]) if "min_samples" in raw_org else None
                ),
                classify_start=_optional_str(raw_org, "classify_start"),
                classify_end=_optional_str(raw_org, "classify_end"),
                exclude_repos=[str(x) for x in exclude],
            )
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid value in [[organizations]] entry {i} "
                f"('{raw_org.get('name', '?')}'): {e}"
            ) from e

        config.organizations.append(org)

    if len(config.repositories) == 0 and len(config.organizations) == 0:
        raise ValueError(
            "Config file must define at least one repository or organization"
        )

    return config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _optional_str(mapping: dict[str, object], key: str) -> str | None:
    """Return mapping[key] as str, or None if the key is absent."""
    value = mapping.get(key)
    if value is None:
        return None
    return str(value)
