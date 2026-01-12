# PR outliers

I want to look at a github repository and take a PR merged within a date range and identify which ones are outliers in terms of PR reviews review time and qualitative reviews.

- I would like to be able to do this using Python as my coding language.
- I would like to use UV as my module dependency manager.
- I want to use ruff as my python linter
- I want to use mypy as the static type checker
- I want to use github actions as my CI/CD pipeline
- I want to run ruff and mypy as part of the CI/CD pipeline as a pre-commit hook and for each PR raised
I want to be able to
- classify PRs that were merged within a certain date range
- classify as outlier reviews
- cache the PR data to a local sqlite DB
- handle github rate limiting via a backoff and wait mechanism
- request multiple PR data concurrently
- I want to use claud code as my AI assistant.
- I want to use MCP agents for my local github
- I want to use MCP agent for my locals sqlite repo


## Outlier Definition

- An outlier review is something that may need more attention.
- It could be a PR that is reviewed too quickly.
- It could be a PR that has a high number of changes.
- It could be a PR that has a high number of complexity.
- It could be a PR that has no comments.
- It could be a PR that has code changes but no unit tests.
- I would like to automatically identify outliers base on the criteria available from the PR review data in github.


## Z Score Calculation
- I would like to use z score calculation to identify outliers.
