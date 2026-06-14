# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.1] - 2026-06-14
- Merge pull request #61 from ghinks/fix/skip-empty-org-incremental-repos
- fix(cli): skip empty org repos during incremental fetch
- Merge pull request #60 from ghinks/feat/skill_pr_branch
- feat(skills): add branching and pr creation guidelines

## [0.1.0] - 2026-05-25
- Update PyPI publish workflow to support major/minor version bumps
- Merge pull request #58 from ghinks/feature/incremental-fetch
- Update README to document --incremental flag
- Reject --incremental when collate-start is provided
- Reject --incremental flag on initial fetch or empty database
- feat: implement incremental fetch functionality

## [0.0.16] - 2026-05-20
- Merge pull request #57 from ghinks/feat/html-report-generation
- docs: remove stale suggestions and implementation summary docs
- docs: add HTML report link to README, remove stale planning docs
- fix: pass threshold through to HTML report generation
- feat: add About This Report section explaining outlier methodology and threshold
- fix: move failed repositories section after results in HTML report
- fix: resolve mypy errors in html_report.py
- refactor: move HTML template to report.html file
- feat: Add HTML report generation for outlier analysis

## [0.0.15] - 2026-05-12
- Merge pull request #56 from ghinks/feat/automate-changelog
- docs: link changelog in pyproject.toml for pypi

## [0.0.14] - 2026-05-12
- Merge pull request #55 from ghinks/feat/automate-changelog
- feat: automate changelog updates in pypi-publish workflow
