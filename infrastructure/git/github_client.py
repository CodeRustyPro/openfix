import os
import logging
from typing import List, Optional
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client with error handling and validation."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub token (optional, uses GITHUB_TOKEN env var if not provided)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")

        if self.token:
            self.client = Github(self.token)
            logger.debug("GitHub client initialized with token")
        else:
            self.client = Github()
            logger.warning(
                "GitHub client initialized without token (rate limits apply)"
            )

    def get_repo_issues(self, repo_url: str) -> List:
        """
        Fetch open issues from a repository.

        Args:
            repo_url: Full GitHub repository URL

        Returns:
            List of Issue objects (empty list on error)

        Raises:
            ValueError: If repo URL is invalid
        """
        # Validate and extract owner/repo from URL
        try:
            repo_name = self._parse_repo_url(repo_url)
        except ValueError as e:
            logger.error(f"Invalid repository URL: {repo_url}")
            raise

        try:
            logger.info(f"Fetching issues from {repo_name}")
            repo = self.client.get_repo(repo_name)

            # Check if issues are enabled
            if not repo.has_issues:
                logger.warning(f"Issues are disabled for {repo_name}")
                return []

            issues = repo.get_issues(state="open")

            # PyGithub get_issues returns both issues and PRs. Filter out PRs.
            issue_list = [i for i in issues if i.pull_request is None]

            logger.info(f"Found {len(issue_list)} open issues")
            return issue_list

        except GithubException as e:
            if e.status == 404:
                logger.error(f"Repository not found: {repo_name}")
            elif e.status == 403:
                logger.error(f"Access denied to {repo_name}. Check token permissions.")
            else:
                logger.error(
                    f"GitHub API error (status {e.status}): {e.data.get('message', str(e))}"
                )
            return []
        except Exception as e:
            logger.error(f"Error fetching issues from {repo_name}: {e}")
            return []

    def _parse_repo_url(self, repo_url: str) -> str:
        """
        Parse repository URL to extract owner/repo.

        Args:
            repo_url: Full GitHub URL (e.g., https://github.com/owner/repo)

        Returns:
            Repository identifier (e.g., "owner/repo")

        Raises:
            ValueError: If URL format is invalid
        """
        if not repo_url:
            raise ValueError("Repository URL cannot be empty")

        try:
            # Handle trailing slashes and .git suffixes
            url = repo_url.rstrip("/")
            if url.endswith(".git"):
                url = url[:-4]
            parts = url.split("/")

            if len(parts) < 2:
                raise ValueError("URL must contain owner and repository name")

            repo_name = f"{parts[-2]}/{parts[-1]}"

            # Basic validation
            if not all(repo_name.split("/")):
                raise ValueError("Invalid owner or repository name")

            return repo_name
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Invalid GitHub URL format: {repo_url}") from e
