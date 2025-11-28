"""Unit tests for GitHub Client."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import GithubException
from infrastructure.git.github_client import GitHubClient


class TestGitHubClient:
    """Test GitHub client functionality."""
    
    def test_init_with_token(self):
        """Test initialization with token."""
        client = GitHubClient(token="test_token")
        assert client.token == "test_token"
    
    def test_init_without_token(self):
        """Test initialization without token."""
        with patch.dict('os.environ', {}, clear=True):
            client = GitHubClient()
            assert client.token is None
    
    def test_parse_repo_url_valid(self):
        """Test parsing valid repository URLs."""
        client = GitHubClient()
        
        assert client._parse_repo_url("https://github.com/owner/repo") == "owner/repo"
        assert client._parse_repo_url("https://github.com/owner/repo/") == "owner/repo"
        assert client._parse_repo_url("https://github.com/owner/repo.git") == "owner/repo"
    
    def test_parse_repo_url_invalid(self):
        """Test parsing invalid repository URLs."""
        client = GitHubClient()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            client._parse_repo_url("")
        
        with pytest.raises(ValueError, match="must contain owner and repository"):
            client._parse_repo_url("not-a-url")
    
    @patch('infrastructure.git.github_client.Github')
    def test_get_repo_issues_success(self, mock_github):
        """Test successful issue fetching."""
        # Setup mocks
        mock_repo = Mock()
        mock_repo.has_issues = True
        
        mock_issue1 = Mock()
        mock_issue1.pull_request = None
        
        mock_issue2 = Mock()
        mock_issue2.pull_request = None
        
        mock_pr = Mock()
        mock_pr.pull_request = Mock()  # This is a PR, should be filtered
        
        mock_repo.get_issues.return_value = [mock_issue1, mock_issue2, mock_pr]
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        # Test
        client = GitHubClient()
        issues = client.get_repo_issues("https://github.com/owner/repo")
        
        assert len(issues) == 2  # PR should be filtered out
        assert mock_issue1 in issues
        assert mock_issue2 in issues
        assert mock_pr not in issues
    
    @patch('infrastructure.git.github_client.Github')
    def test_get_repo_issues_disabled(self, mock_github):
        """Test fetching when issues are disabled."""
        mock_repo = Mock()
        mock_repo.has_issues = False
        
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient()
        issues = client.get_repo_issues("https://github.com/owner/repo")
        
        assert issues == []
    
    @patch('infrastructure.git.github_client.Github')
    def test_get_repo_issues_not_found(self, mock_github):
        """Test handling of 404 errors."""
        mock_github_instance = Mock()
        mock_error = GithubException(404, {"message": "Not Found"})
        mock_github_instance.get_repo.side_effect = mock_error
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient()
        issues = client.get_repo_issues("https://github.com/owner/repo")
        
        assert issues == []
    
    @patch('infrastructure.git.github_client.Github')
    def test_get_repo_issues_forbidden(self, mock_github):
        """Test handling of 403 errors."""
        mock_github_instance = Mock()
        mock_error = GithubException(403, {"message": "Forbidden"})
        mock_github_instance.get_repo.side_effect = mock_error
        mock_github.return_value = mock_github_instance
        
        client = GitHubClient()
        issues = client.get_repo_issues("https://github.com/owner/repo")
        
        assert issues == []
