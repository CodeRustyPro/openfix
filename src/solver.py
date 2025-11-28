import os
from .github_client import GitHubClient
from .ingest import Ingestor
from .llm import GeminiLLM
from rich.console import Console
from rich.markdown import Markdown

console = Console()

class IssueSolver:
    def __init__(self):
        self.github_client = GitHubClient()
        self.ingestor = Ingestor()
        self.llm = GeminiLLM()

    def solve(self, repo_url):
        # Clear previous solutions
        if os.path.exists("solutions.md"):
            os.remove("solutions.md")
            
        console.print(f"[bold green]Starting analysis for {repo_url}[/bold green]")

        # 1. Fetch Issues
        issues = self.github_client.get_repo_issues(repo_url)
        if not issues:
            console.print("[red]No open issues found or failed to fetch issues.[/red]")
            return

        console.print(f"Found {len(issues)} open issues.")

        # 2. Ingest Codebase
        console.print("Ingesting codebase...")
        temp_dir = self.ingestor.clone_repo(repo_url)
        if not temp_dir:
            console.print("[red]Failed to clone repository.[/red]")
            return
        
        codebase_context = self.ingestor.get_codebase_context()
        console.print(f"Codebase context length: {len(codebase_context)} characters.")

        # 3. Process Issues (Limit to top 3 for now to avoid huge costs/time)
        count = 0
        for issue in issues:
            if count >= 3:
                break
            
            console.print(f"\n[bold blue]Analyzing Issue #{issue.number}: {issue.title}[/bold blue]")
            
            try:
                solution = self.llm.generate_solution(issue.title, issue.body, codebase_context)
                
                console.print(f"[bold]Proposed Solution for Issue #{issue.number}:[/bold]")
                console.print(Markdown(solution))
                
                with open("solutions.md", "a") as f:
                    f.write(f"\n# Issue #{issue.number}: {issue.title}\n\n")
                    f.write(solution)
                    f.write("\n\n---\n")
                
            except Exception as e:
                console.print(f"[red]Error generating solution: {e}[/red]")
            
            count += 1

        # Cleanup
        self.ingestor.cleanup()
