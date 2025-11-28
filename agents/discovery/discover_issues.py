#!/usr/bin/env python3
"""Issue Discovery Agent."""
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from infrastructure.git.github_client import GitHubClient
from infrastructure.llm_pool.client import GeminiLLM

class IssueDiscoveryAgent:
    def __init__(self, repo_url: str, output_dir: str = "artifacts"):
        self.repo_url = repo_url
        self.output_dir = Path(output_dir)
        self.gh_client = GitHubClient()
        self.llm_client = GeminiLLM()
        
    def discover(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover, triage, and rank issues.
        
        Args:
            limit: Max number of issues to analyze
            
        Returns:
            List of top ranked issues
        """
        print(f"Fetching issues for {self.repo_url}...")
        issues = self.gh_client.get_repo_issues(self.repo_url)
        
        if not issues:
            print("No open issues found.")
            return []
            
        print(f"Found {len(issues)} open issues. Analyzing top {limit}...")
        
        candidates = []
        
        # Analyze top N issues
        for i, issue in enumerate(issues[:limit]):
            print(f"Analyzing #{issue.number}: {issue.title}...")
            
            labels = [l.name for l in issue.labels]
            
            # Skip if explicitly labeled as 'wontfix', 'question', 'invalid'
            skip_labels = {'wontfix', 'question', 'invalid', 'documentation'}
            if any(l in skip_labels for l in labels):
                print(f"  Skipping due to labels: {labels}")
                continue
                
            triage_result = self.llm_client.triage_issue(
                issue.title,
                issue.body or "",
                labels
            )
            
            if triage_result.get('is_suitable'):
                print(f"  ✓ Suitable (Score: {triage_result.get('priority_score')})")
                candidate = {
                    "issue_number": issue.number,
                    "title": issue.title,
                    "body": (issue.body or "")[:500] + "...", # Truncate for summary
                    "labels": labels,
                    "triage_data": triage_result
                }
                candidates.append(candidate)
            else:
                print(f"  ✗ Not suitable: {triage_result.get('reason')}")
        
        # Rank candidates
        # Sort by priority_score (descending), then complexity (low > medium > high)
        complexity_map = {"low": 3, "medium": 2, "high": 1, "unknown": 0}
        
        candidates.sort(key=lambda x: (
            x['triage_data'].get('priority_score', 0),
            complexity_map.get(x['triage_data'].get('estimated_complexity_score', 'unknown').lower(), 0)
        ), reverse=True)
        
        # Take top 5
        top_candidates = candidates[:5]
        
        # Save to artifacts
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "issues.json"
        
        with open(output_path, 'w') as f:
            json.dump(top_candidates, f, indent=2)
            
        print(f"\nSaved {len(top_candidates)} candidates to {output_path}")
        return top_candidates

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--limit", type=int, default=10, help="Max issues to analyze")
    args = parser.parse_args()
    
    agent = IssueDiscoveryAgent(args.repo_url)
    agent.discover(args.limit)
