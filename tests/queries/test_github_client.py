import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from review_classification.queries.github_client import fetch_prs
from review_classification.sqlite.models import PullRequest


class TestGithubClient(unittest.TestCase):
    @patch("review_classification.queries.github_client.Github")
    @patch("review_classification.queries.github_client.fetch_repo")
    def test_fetch_prs_success(self, mock_fetch_repo: MagicMock, _: MagicMock) -> None:
        # Setup
        mock_repo = MagicMock()
        mock_fetch_repo.return_value = mock_repo

        # Mock PRs
        pr1 = MagicMock()
        pr1.number = 1
        pr1.title = "PR 1"
        pr1.user.login = "user1"
        pr1.created_at = datetime(2023, 1, 10, 12, 0, 0)
        pr1.merged_at = datetime(2023, 1, 11, 12, 0, 0)
        pr1.closed_at = datetime(2023, 1, 11, 12, 0, 0)
        pr1.additions = 10
        pr1.deletions = 5
        pr1.changed_files = 2
        pr1.comments = 1
        pr1.review_comments = 0
        pr1.state = "closed"
        pr1.html_url = "http://github.com/owner/repo/pull/1"

        # Setup the generator behavior
        # fetch_prs calls fetch_prs_generator twice (one ignored, one used)
        # We just ensure get_pulls returns our list
        mock_repo.get_pulls.return_value = [pr1]

        # Execute
        results = fetch_prs("owner/repo", token="dummy")

        # Verify
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], PullRequest)
        self.assertEqual(results[0].number, 1)
        self.assertEqual(results[0].title, "PR 1")
        self.assertEqual(results[0].author, "user1")

    @patch("review_classification.queries.github_client.Github")
    @patch("review_classification.queries.github_client.fetch_repo")
    def test_fetch_prs_date_filtering(
        self, mock_fetch_repo: MagicMock, _: MagicMock
    ) -> None:
        mock_repo = MagicMock()
        mock_fetch_repo.return_value = mock_repo

        # Dates (UTC)
        date_target = datetime(2023, 6, 15, tzinfo=UTC)
        date_before = datetime(2023, 1, 1, tzinfo=UTC)
        date_after = datetime(2023, 12, 31, tzinfo=UTC)

        # PRs
        # 1. New (After end_date) - Should be skipped
        pr_new = MagicMock()
        pr_new.created_at = date_after
        pr_new.number = 3

        # 2. Target (In range) - Should be included
        pr_mid = MagicMock()
        pr_mid.created_at = date_target
        pr_mid.number = 2
        pr_mid.user.login = "user"
        pr_mid.title = "Target"
        pr_mid.merged_at = None
        pr_mid.closed_at = None
        pr_mid.additions = 0
        pr_mid.deletions = 0
        pr_mid.changed_files = 0
        pr_mid.comments = 0
        pr_mid.review_comments = 0
        pr_mid.state = "open"
        pr_mid.html_url = "url"

        # 3. Old (Before start_date) - Should trigger break
        pr_old = MagicMock()
        pr_old.created_at = date_before
        pr_old.number = 1

        # The list is returned in desc order as requested
        mock_repo.get_pulls.return_value = [pr_new, pr_mid, pr_old]

        # Execute with date range
        start_str = "2023-02-01"
        end_str = "2023-10-01"

        results = fetch_prs(
            "owner/repo", start_date=start_str, end_date=end_str, token="dummy"
        )

        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].number, 2)

    @patch("review_classification.queries.github_client.Github")
    @patch("review_classification.queries.github_client.fetch_repo")
    def test_fetch_prs_no_token(self, _: MagicMock, mock_github: MagicMock) -> None:
        # Test that it tries to grab env var if no token passed
        with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
            fetch_prs("owner/repo")
            mock_github.assert_called_with("env_token")

    @patch("review_classification.queries.github_client.Github")
    @patch("review_classification.queries.github_client.fetch_repo")
    def test_fetch_prs_empty(self, mock_fetch_repo: MagicMock, _: MagicMock) -> None:
        mock_repo = MagicMock()
        mock_fetch_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = []

        results = fetch_prs("owner/repo", token="dummy")
        self.assertEqual(len(results), 0)
