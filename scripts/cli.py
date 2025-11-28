#!/usr/bin/env python3
"""Interactive CLI for OpenFix patch approval workflow.

Provides commands for:
- Discovering and triaging issues
- Generating patches with preview
- Approving patches for PR creation
- Managing patch approvals
"""
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table


console = Console()


def show_patch_preview(patch_path: str, max_lines: int = 50):
    """Display patch diff with syntax highlighting."""
    try:
        with open(patch_path, "r") as f:
            patch_content = f.read()

        # Show first N lines
        lines = patch_content.split("\n")
        preview = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            preview += f"\n... ({len(lines) - max_lines} more lines)"

        syntax = Syntax(preview, "diff", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Patch Preview", border_style="cyan"))

        return True
    except Exception as e:
        console.print(f"[red]Error reading patch: {e}[/red]")
        return False


def show_confidence_report(report_path: str):
    """Display confidence assessment."""
    try:
        with open(report_path, "r") as f:
            report = json.load(f)

        confidence = report.get("confidence", {})
        score = confidence.get("confidence_score", 0)
        risk = confidence.get("risk_rating", "Unknown")
        recommendation = report.get("summary", {}).get("recommendation", "")

        # Create table
        table = Table(title="Confidence Assessment", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Confidence Score", f"{score}/100")
        table.add_row("Risk Rating", risk)

        factors = confidence.get("factors", {})
        if "triage" in factors:
            table.add_row("  ├─ Triage", f"{factors['triage']:.1f}")
        if "complexity" in factors:
            table.add_row("  ├─ Complexity", f"{factors['complexity']:.1f}")
        if "validation" in factors:
            table.add_row("  ├─ Validation", f"{factors['validation']:.1f}")
        if "repair_attempts" in factors:
            table.add_row("  └─ Repair", f"{factors['repair_attempts']:.1f}")

        console.print(table)
        console.print(f"\n[bold]{recommendation}[/bold]\n")

        return True
    except Exception as e:
        console.print(f"[red]Error reading report: {e}[/red]")
        return False


def approve_patch_interactive(report_path: str, patch_path: str, repo_url: str) -> bool:
    """Interactive approval workflow for patch."""
    console.print("\n[bold cyan]═══ OpenFix Patch Approval ═══[/bold cyan]\n")

    # Show confidence report
    if not show_confidence_report(report_path):
        return False

    # Show patch preview
    if not show_patch_preview(patch_path):
        return False

    # Ask for approval
    approve_patch = Confirm.ask("\n[yellow]Do you want to approve this patch?[/yellow]")

    if not approve_patch:
        console.print("[red]Patch rejected.[/red]")
        return False

    console.print("[green]✓ Patch approved![/green]")

    # Ask about PR creation
    create_pr = Confirm.ask("\n[yellow]Create a GitHub Pull Request?[/yellow]")

    if not create_pr:
        console.print("[blue]Patch approved but PR creation skipped.[/blue]")
        return True

    # Create PR
    console.print("\n[cyan]Creating Pull Request...[/cyan]")

    try:
        cmd = [
            sys.executable,
            "scripts/automate_full_pipeline.py",
            "--repo-url",
            repo_url,
            "--create-pr",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Extract PR URL from output
            for line in result.stdout.split("\n"):
                if "PR:" in line or "PR Created:" in line:
                    console.print(f"[green bold]{line}[/green bold]")

            console.print("\n[green]✓ Pull Request created successfully![/green]")
            return True
        else:
            console.print(f"[red]✗ PR creation failed: {result.stderr}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error creating PR: {e}[/red]")
        return False


def cmd_discover(repo_url: str, limit: int = 10):
    """Discover and triage issues."""
    console.print(f"\n[cyan]Discovering issues in {repo_url}...[/cyan]\n")

    cmd = [
        sys.executable,
        "agents/discovery/discover_issues.py",
        repo_url,
        "--limit",
        str(limit),
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        console.print(
            "\n[green]✓ Discovery complete! Results saved to artifacts/issues.json[/green]"
        )
    else:
        console.print("\n[red]✗ Discovery failed[/red]")


def cmd_solve(repo_url: str, issue_number: int, no_confirm: bool = False):
    """Generate patch for specific issue."""
    console.print(f"\n[cyan]Generating patch for issue #{issue_number}...[/cyan]\n")

    cmd = [
        sys.executable,
        "scripts/run_e2e.py",
        "--repo",
        repo_url,
        "--issue",
        str(issue_number),
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:
        console.print("\n[red]✗ Patch generation failed[/red]")
        return

    console.print("\n[green]✓ Patch generated![/green]")

    # Find report and patch
    report_path = "artifacts/final_report.json"
    patch_path = f"data/patches/issue-{issue_number}/fix.patch"

    if no_confirm:
        console.print("[yellow]Auto-approving (--no-confirm)[/yellow]")
        approve_patch_interactive(report_path, patch_path, repo_url)
    else:
        approve_patch_interactive(report_path, patch_path, repo_url)


def cmd_status():
    """Show pending patches and approvals."""
    console.print("\n[cyan]OpenFix Status[/cyan]\n")

    # Check for pending patches
    patches_dir = Path("data/patches")
    if patches_dir.exists():
        patches = list(patches_dir.glob("issue-*/fix.patch"))

        table = Table(title="Pending Patches")
        table.add_column("Issue", style="cyan")
        table.add_column("Patch", style="green")
        table.add_column("Status", style="yellow")

        for patch in patches:
            issue_num = patch.parent.name.replace("issue-", "")
            table.add_row(f"#{issue_num}", str(patch), "Pending Review")

        console.print(table)
    else:
        console.print("[yellow]No patches found[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="OpenFix CLI - Interactive patch approval workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover issues
  openfix discover https://github.com/owner/repo

  # Generate patch for specific issue
  openfix solve https://github.com/owner/repo --issue 123

  # Auto-approve (skip confirmation)
  openfix solve https://github.com/owner/repo --issue 123 --no-confirm

  # Check status
  openfix status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # discover command
    discover_parser = subparsers.add_parser(
        "discover", help="Discover and triage issues"
    )
    discover_parser.add_argument("repo_url", help="GitHub repository URL")
    discover_parser.add_argument(
        "--limit", type=int, default=10, help="Max issues to analyze"
    )

    # solve command
    solve_parser = subparsers.add_parser("solve", help="Generate patch for issue")
    solve_parser.add_argument("repo_url", help="GitHub repository URL")
    solve_parser.add_argument("--issue", type=int, required=True, help="Issue number")
    solve_parser.add_argument(
        "--no-confirm", action="store_true", help="Skip approval prompts"
    )
    solve_parser.add_argument(
        "--approve-patch", action="store_true", help="Auto-approve patch"
    )
    solve_parser.add_argument(
        "--approve-pr", action="store_true", help="Auto-approve PR creation"
    )

    # status command
    status_parser = subparsers.add_parser("status", help="Show pending patches")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "discover":
        cmd_discover(args.repo_url, args.limit)
    elif args.command == "solve":
        no_confirm = args.no_confirm or (args.approve_patch and args.approve_pr)
        cmd_solve(args.repo_url, args.issue, no_confirm)
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()
