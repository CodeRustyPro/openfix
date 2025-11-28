"""PR Creator for OpenFix generated patches.

Creates draft GitHub Pull Requests with:
- AI disclosure and attribution
- Patch explanation and risk assessment
- Links to artifacts and validation results
- Custom labels for tracking
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PRCreator:
    """Create GitHub Pull Requests for patches."""

    def __init__(self, repo_url: str):
        """
        Initialize PR creator.

        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)

        Raises:
            ValueError: If GITHUB_TOKEN not found or repo URL invalid
        """
        self.repo_url = repo_url

        # Extract owner/repo from URL
        parts = repo_url.rstrip("/").split("/")
        self.repo_name = f"{parts[-2]}/{parts[-1]}"

        # Initialize GitHub client
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError(
                "GITHUB_TOKEN not found in environment. PR creation requires authentication."
            )

        self.gh = Github(token)

        try:
            self.repo = self.gh.get_repo(self.repo_name)
            logger.info(f"PR creator initialized for {self.repo_name}")
        except GithubException as e:
            logger.error(f"Failed to access repository {self.repo_name}: {e}")
            raise ValueError(f"Cannot access repository: {e}")

    def create_pr(self, patch_data: Dict[str, Any], repo_dir: str) -> Optional[str]:
        """
        Create a draft PR from patch data.

        Args:
            patch_data: Dict containing:
                - issue_number: int
                - patch_path: str (path to .patch file)
                - confidence_score: float
                - risk_rating: str
                - artifacts_dir: str
                - explanation: str (optional)

            repo_dir: Path to cloned repository

        Returns:
            PR URL if successful, None otherwise
        """
        issue_number = patch_data["issue_number"]
        patch_path = patch_data["patch_path"]
        confidence = patch_data.get("confidence_score", 0)
        risk = patch_data.get("risk_rating", "Unknown")

        try:
            # Get the issue
            logger.info(f"Creating PR for issue #{issue_number}")
            issue = self.repo.get_issue(issue_number)

            # Create branch name
            branch_name = f"openfix/issue-{issue_number}"

            # Check if branch already exists
            try:
                self.repo.get_branch(branch_name)
                logger.warning(
                    f"Branch {branch_name} already exists, using timestamped name"
                )
                import time

                branch_name = f"openfix/issue-{issue_number}-{int(time.time())}"
            except GithubException:
                pass  # Branch doesn't exist, good

            # Apply patch and push to branch
            try:
                self._apply_and_push_patch(patch_path, branch_name, repo_dir)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to apply patch: {e}")
                return None

            # Create PR body
            pr_body = self._generate_pr_body(issue, patch_data)

            # Create PR
            logger.info(f"Creating draft PR on branch {branch_name}")
            pr = self.repo.create_pull(
                title=f"[OpenFix] Fix #{issue_number}: {issue.title}",
                body=pr_body,
                head=branch_name,
                base="main",  # TODO: Make configurable or detect default branch
                draft=True,
            )

            # Add labels (create if they don't exist)
            self._add_labels(pr, risk)

            # Comment on original issue
            self._comment_on_issue(issue, pr, confidence, risk)

            logger.info(f"✓ PR created successfully: {pr.html_url}")
            return pr.html_url

        except GithubException as e:
            logger.error(
                f"GitHub API error creating PR: {e.data.get('message', str(e))}"
            )
            return None
        except Exception as e:
            logger.error(f"Error creating PR: {e}", exc_info=True)
            return None

    def _apply_and_push_patch(self, patch_path: str, branch_name: str, repo_dir: str):
        """
        Apply patch and push to new branch.

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        # Navigate to repo directory
        original_dir = os.getcwd()

        try:
            os.chdir(repo_dir)
            logger.debug(f"Working in {repo_dir}")

            # Create and checkout new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name], check=True, capture_output=True
            )
            logger.debug(f"Created branch {branch_name}")

            # Apply patch
            subprocess.run(
                ["git", "apply", patch_path], check=True, capture_output=True
            )
            logger.debug("Patch applied successfully")

            # Stage changes
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

            # Commit
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"Fix issue via OpenFix AI\n\nCo-authored-by: OpenFix AI <openfix@ai.dev>",
                ],
                check=True,
                capture_output=True,
            )
            logger.debug("Changes committed")

            # Push to origin
            subprocess.run(
                ["git", "push", "origin", branch_name], check=True, capture_output=True
            )
            logger.debug(f"Pushed to origin/{branch_name}")

        finally:
            os.chdir(original_dir)

    def _generate_pr_body(self, issue, patch_data: Dict[str, Any]) -> str:
        """Generate PR description with AI disclosure."""
        confidence = patch_data.get("confidence_score", 0)
        risk = patch_data.get("risk_rating", "Unknown")
        artifacts_dir = patch_data.get("artifacts_dir", "")
        explanation = patch_data.get("explanation", "Automated fix generated")
        repair_attempts = patch_data.get("repair_attempts", 0)

        body = f"""## 🤖 AI-Generated Fix

> **⚠️ AI Disclosure**: This pull request was automatically generated by [OpenFix](https://github.com/yourusername/openfix), an AI-powered issue resolution tool.

### Issue
Fixes #{issue.number}: {issue.title}

### Explanation
{explanation}

### Confidence Assessment
- **Confidence Score**: {confidence}/100
- **Risk Rating**: {risk}
- **Repair Iterations**: {repair_attempts}

### Validation
"""

        if patch_data.get("validation_passed"):
            body += "✅ **Passed** automated validation\n"
        else:
            body += "❌ **Failed** automated validation - Manual review required\n"

        body += f"""
### Artifacts
Run ID: `{Path(artifacts_dir).name if artifacts_dir else 'N/A'}`
- [View Artifacts]({artifacts_dir})

### Review Checklist
- [ ] Code changes are correct and complete
- [ ] No unintended side effects
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if needed)

---
*Generated with ❤️ by OpenFix AI*
"""

        return body

    def _add_labels(self, pr, risk: str):
        """Add labels to PR, creating them if necessary."""
        labels_to_add = ["ai-generated", "openfix"]

        if risk == "Low":
            labels_to_add.append("low-risk")
        elif risk == "High":
            labels_to_add.append("high-risk")

        try:
            pr.add_to_labels(*labels_to_add)
            logger.debug(f"Added labels: {labels_to_add}")
        except GithubException as e:
            logger.warning(f"Failed to add labels: {e.data.get('message', str(e))}")

    def _comment_on_issue(self, issue, pr, confidence: float, risk: str):
        """Post comment on original issue linking to PR."""
        try:
            issue.create_comment(
                f"🤖 I've generated a potential fix for this issue!\n\n"
                f"**PR**: #{pr.number}\n"
                f"**Confidence**: {confidence}/100 ({risk} risk)\n\n"
                f"Please review the draft PR and let me know if you have any feedback."
            )
            logger.debug(f"Posted comment on issue #{issue.number}")
        except GithubException as e:
            logger.warning(
                f"Failed to comment on issue: {e.data.get('message', str(e))}"
            )
