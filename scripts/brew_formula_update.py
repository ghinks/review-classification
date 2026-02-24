"""Update the Homebrew formula with a new package version.

Downloads the sdist from PyPI for the given version, calculates its SHA-256,
and rewrites the url/sha256 fields in the formula file.

Usage:
    uv run python scripts/brew_formula_update.py \
        --version 0.0.3 \
        --formula HomebrewFormula/review-classification.rb
"""

import argparse
import hashlib
import re
import urllib.error
import urllib.request

PYPI_SDIST_URL = (
    "https://files.pythonhosted.org/packages/source/r"
    "/review-classification/review_classification-{version}.tar.gz"
)

_TIMEOUT_SECONDS = 60


def sha256_of_url(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
            return hashlib.sha256(response.read()).hexdigest()
    except urllib.error.HTTPError as exc:
        msg = f"HTTP error downloading {url}: {exc.code} {exc.reason}"
        raise SystemExit(msg) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error downloading {url}: {exc.reason}") from exc


def update_formula(formula_path: str, version: str) -> None:
    url = PYPI_SDIST_URL.format(version=version)
    print(f"Downloading {url} to compute SHA-256 \u2026")
    digest = sha256_of_url(url)
    print(f"SHA-256: {digest}")

    with open(formula_path) as fh:
        content = fh.read()

    # Replace url line (flexible whitespace)
    updated, url_count = re.subn(
        r'(\s+url ")https://[^"]+review_classification-[^"]+\.tar\.gz(")',
        rf'\g<1>{url}\g<2>',
        content,
    )
    if url_count == 0:
        raise SystemExit(f"Could not find main package url line in {formula_path}")

    # Replace the first sha256 line (the main package; resource sha256s are preserved)
    updated, sha_count = re.subn(
        r'(\s+sha256 ")[0-9a-f]{64}(")',
        rf'\g<1>{digest}\g<2>',
        updated,
        count=1,
    )
    if sha_count == 0:
        raise SystemExit(f"Could not find main package sha256 line in {formula_path}")

    with open(formula_path, "w") as fh:
        fh.write(updated)

    print(f"Updated {formula_path} to version {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Homebrew formula version")
    parser.add_argument("--version", required=True, help="New package version")
    parser.add_argument("--formula", required=True, help="Path to the .rb formula file")
    args = parser.parse_args()
    update_formula(args.formula, args.version)


if __name__ == "__main__":
    main()
