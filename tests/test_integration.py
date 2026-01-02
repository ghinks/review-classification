import os
import shutil
import subprocess

import pytest


@pytest.mark.integration
@pytest.mark.timeout(300)
def test_review_classify_integration() -> None:
    """
    Integration test that runs the full CLI command against a real repo.
    Required: 'gh' CLI tool must be authenticated.
    """
    # 1. Get GitHub Token
    if not shutil.which("gh"):
        pytest.skip("GitHub CLI (gh) not found")

    try:
        # Capture token from gh cli
        token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except subprocess.CalledProcessError:
        pytest.skip("Could not get GITHUB_TOKEN from gh CLI. Is it authenticated?")

    # 2. Prepare environment
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token

    # 3. Construct command
    # "uv run review-classify expressjs/express --start 2024-12-01 --end 2024-12-31"
    cmd = [
        "uv",
        "run",
        "review-classify",
        "expressjs/express",
        "--start",
        "2024-12-01",
        "--end",
        "2024-12-31",
    ]

    # 4. Run command
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    # 5. Assertions
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

    assert result.returncode == 0, (
        f"Command failed with return code {result.returncode}"
    )
    # Check for expected output strings
    assert "Fetching PRs for expressjs/express" in result.stdout
    assert "Saving" in result.stdout
