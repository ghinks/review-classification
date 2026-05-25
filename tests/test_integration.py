import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_NAME = "expressjs/express"


@dataclass(frozen=True)
class DateWindows:
    fetch_start: str
    fetch_end: str
    classify_start: str
    classify_end: str


FetchArgsBuilder = Callable[[DateWindows, Path], list[str]]


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    result: subprocess.CompletedProcess[str]


def _date_windows() -> DateWindows:
    today = datetime.now(UTC).date()
    fetch_end = today.strftime("%Y-%m-%d")
    fetch_start = (today - timedelta(days=182)).strftime("%Y-%m-%d")
    classify_end = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    return DateWindows(
        fetch_start=fetch_start,
        fetch_end=fetch_end,
        classify_start=fetch_start,
        classify_end=classify_end,
    )


def _github_env() -> dict[str, str]:
    if not shutil.which("gh"):
        pytest.skip("GitHub CLI (gh) not found")

    try:
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except subprocess.CalledProcessError:
        pytest.skip("Could not get GITHUB_TOKEN from gh CLI. Is it authenticated?")

    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token
    return env


def _run_cli(
    args: list[str],
    env: dict[str, str],
    cwd: Path,
) -> CommandResult:
    command_env = env.copy()
    command_env.setdefault("UV_CACHE_DIR", str(cwd / ".uv-cache"))
    command = ["uv", "run", "review-classify", *args]
    result = subprocess.run(
        command,
        cwd=cwd,
        env=command_env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "Command failed.\n"
            f"Command: {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
    return CommandResult(command=command, result=result)


@pytest.fixture(scope="session")
def github_env() -> dict[str, str]:
    return _github_env()


@pytest.fixture(scope="session")
def date_windows() -> DateWindows:
    return _date_windows()


@pytest.fixture
def isolated_workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(scope="module")
def fetched_workspace(
    tmp_path_factory: pytest.TempPathFactory,
    github_env: dict[str, str],
    date_windows: DateWindows,
) -> Iterator[Path]:
    workspace = tmp_path_factory.mktemp("integration-db")
    fetch_result = _run_cli(
        [
            "fetch",
            "--repo",
            REPO_NAME,
            "--collate-start",
            date_windows.fetch_start,
            "--collate-end",
            date_windows.fetch_end,
        ],
        env=github_env,
        cwd=workspace,
    )

    assert f"Fetching {REPO_NAME}..." in fetch_result.result.stdout
    assert "Saving" in fetch_result.result.stdout
    assert workspace.joinpath("review_classification.db").exists()
    yield workspace


@pytest.mark.integration
@pytest.mark.timeout(1800)
@pytest.mark.parametrize(
    ("args_builder", "expected_stdout"),
    [
        (
            lambda _dates, _workspace: ["fetch", "--repo", REPO_NAME],
            "Successfully saved",
        ),
        (
            lambda dates, _workspace: [
                "fetch",
                "--repo",
                REPO_NAME,
                "--collate-start",
                dates.fetch_start,
                "--collate-end",
                dates.fetch_end,
            ],
            "Successfully saved",
        ),
        (
            lambda dates, _workspace: [
                "fetch",
                "--repo",
                REPO_NAME,
                "--reset-db",
                "--collate-start",
                dates.fetch_start,
                "--collate-end",
                dates.fetch_end,
            ],
            "Database reset complete.",
        ),
        (
            lambda dates, workspace: [
                "fetch",
                "--config",
                str(_write_fetch_config(workspace, dates)),
            ],
            "Successfully saved",
        ),
    ],
    ids=["fetch-default", "fetch-with-dates", "fetch-reset-db", "fetch-config"],
)
def test_fetch_examples_integration(
    args_builder: FetchArgsBuilder,
    expected_stdout: str,
    github_env: dict[str, str],
    date_windows: DateWindows,
    isolated_workspace: Path,
) -> None:
    result = _run_cli(
        args_builder(date_windows, isolated_workspace),
        env=github_env,
        cwd=isolated_workspace,
    )

    assert f"Fetching {REPO_NAME}..." in result.result.stdout
    assert "Saving" in result.result.stdout
    assert expected_stdout in result.result.stdout
    assert isolated_workspace.joinpath("review_classification.db").exists()


@pytest.mark.integration
@pytest.mark.timeout(1800)
def test_classify_example_table_output(
    github_env: dict[str, str],
    date_windows: DateWindows,
    fetched_workspace: Path,
) -> None:
    result = _run_cli(
        [
            "classify",
            "--repo",
            REPO_NAME,
            "--start",
            date_windows.classify_start,
            "--end",
            date_windows.classify_end,
            "--min-samples",
            "5",
        ],
        env=github_env,
        cwd=fetched_workspace,
    )

    assert (
        "outlier" in result.result.stdout
        or "could not be classified" in result.result.stdout
    )


@pytest.mark.integration
@pytest.mark.timeout(1800)
def test_classify_example_stricter_threshold(
    github_env: dict[str, str],
    date_windows: DateWindows,
    fetched_workspace: Path,
) -> None:
    result = _run_cli(
        [
            "classify",
            "--repo",
            REPO_NAME,
            "--start",
            date_windows.classify_start,
            "--end",
            date_windows.classify_end,
            "--threshold",
            "3.0",
            "--min-samples",
            "5",
        ],
        env=github_env,
        cwd=fetched_workspace,
    )

    assert result.result.stdout.strip() != ""


@pytest.mark.integration
@pytest.mark.timeout(1800)
def test_classify_example_json_output(
    github_env: dict[str, str],
    date_windows: DateWindows,
    fetched_workspace: Path,
) -> None:
    result = _run_cli(
        [
            "classify",
            "--repo",
            REPO_NAME,
            "--start",
            date_windows.classify_start,
            "--end",
            date_windows.classify_end,
            "--format",
            "json",
            "--min-samples",
            "5",
        ],
        env=github_env,
        cwd=fetched_workspace,
    )

    payload = json.loads(result.result.stdout)
    assert isinstance(payload, list)
    if payload:
        first_item = payload[0]
        assert first_item["is_outlier"] is True
        assert "pr_number" in first_item
        assert "outlier_features" in first_item


@pytest.mark.integration
@pytest.mark.timeout(1800)
def test_classify_example_exclude_primary_merged(
    github_env: dict[str, str],
    date_windows: DateWindows,
    fetched_workspace: Path,
) -> None:
    result = _run_cli(
        [
            "classify",
            "--repo",
            REPO_NAME,
            "--start",
            date_windows.classify_start,
            "--end",
            date_windows.classify_end,
            "--exclude-primary-merged",
            "--min-samples",
            "5",
        ],
        env=github_env,
        cwd=fetched_workspace,
    )

    assert result.result.stdout.strip() != ""


def _write_fetch_config(workspace: Path, dates: DateWindows) -> Path:
    config_path = workspace / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[defaults]",
                f'collate_start = "{dates.fetch_start}"',
                f'collate_end = "{dates.fetch_end}"',
                "",
                "[[repositories]]",
                f'name = "{REPO_NAME}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path
