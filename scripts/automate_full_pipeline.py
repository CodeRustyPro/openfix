#!/usr/bin/env python3
"""Full automation orchestrator for OpenFix.

Loads top-ranked issue from discovery, runs E2E pipeline, and generates final report.
"""
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_top_issue(issues_file: str = "artifacts/issues.json") -> dict:
    """Load the top-ranked issue from discovery output."""
    try:
        with open(issues_file, "r") as f:
            issues = json.load(f)

        if not issues:
            raise ValueError("No issues found in discovery output")

        # Issues are already ranked, take first
        return issues[0]
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Issue discovery output not found at {issues_file}. "
            "Run 'python agents/discovery/discover_issues.py' first."
        )


def run_e2e_pipeline(repo_url: str, issue_number: int) -> dict:
    """Run the E2E pipeline for the given issue."""
    print(f"\n{'='*60}")
    print(f"Running E2E Pipeline")
    print(f"{'='*60}")
    print(f"Repository: {repo_url}")
    print(f"Issue: #{issue_number}")
    print(f"{'='*60}\n")

    # Run E2E script
    cmd = [
        sys.executable,
        "scripts/run_e2e.py",
        "--repo",
        repo_url,
        "--issue",
        str(issue_number),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    # Parse output for metrics
    output = result.stdout + result.stderr

    # Extract metrics from output
    patch_generated = "✓ Patch generated:" in output
    validation_passed = "✓ Validation: PASSED" in output
    run_id = None
    patch_path = None

    # Extract run ID
    for line in output.split("\n"):
        if "Run ID:" in line:
            run_id = line.split("Run ID:")[-1].strip()
        if "✓ Patch generated:" in line:
            patch_path = line.split("✓ Patch generated:")[-1].strip()

    # Count repair attempts from logs
    repair_attempts = output.count("Attempting to repair patch")

    return {
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "run_id": run_id,
        "patch_generated": patch_generated,
        "validation_passed": validation_passed,
        "patch_path": patch_path,
        "repair_attempts": repair_attempts,
        "output": output,
    }


from infrastructure.confidence.scorer import ConfidenceScorer
from agents.orchestrator.pr_creator import PRCreator


def generate_final_report(
    issue_data: dict, e2e_result: dict, output_file: str = "artifacts/final_report.json"
) -> dict:
    """Generate and save final automation report."""

    # Calculate confidence score
    scorer = ConfidenceScorer()
    confidence_data = scorer.calculate_confidence(
        {
            "patch_generated": e2e_result["patch_generated"],
            "triage_score": issue_data["triage_data"].get("priority_score", 5),
            "complexity": issue_data["triage_data"].get(
                "estimated_complexity_score", "medium"
            ),
            "validation_passed": e2e_result["validation_passed"],
            "repair_attempts": e2e_result["repair_attempts"],
        }
    )

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "issue": {
            "issue_number": issue_data["issue_number"],
            "title": issue_data["title"],
            "labels": issue_data["labels"],
            "triage_score": issue_data["triage_data"].get("priority_score"),
            "complexity": issue_data["triage_data"].get("estimated_complexity_score"),
        },
        "pipeline_result": {
            "success": e2e_result["success"],
            "exit_code": e2e_result["exit_code"],
            "run_id": e2e_result["run_id"],
            "patch_generated": e2e_result["patch_generated"],
            "validation_passed": e2e_result["validation_passed"],
            "patch_path": e2e_result["patch_path"],
            "repair_attempts": e2e_result["repair_attempts"],
        },
        "confidence": confidence_data,
        "summary": {
            "status": "SUCCESS" if e2e_result["success"] else "FAILED",
            "patch_created": e2e_result["patch_generated"],
            "patch_validated": e2e_result["validation_passed"],
            "refinement_iterations": e2e_result["repair_attempts"],
            "recommendation": scorer.get_recommendation(confidence_data),
        },
    }

    # Save report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Final Report Saved: {output_file}")
    print(f"{'='*60}")

    return report


def main():
    parser = argparse.ArgumentParser(description="OpenFix Full Automation Orchestrator")
    parser.add_argument("--repo-url", help="Override repository URL")
    parser.add_argument(
        "--issues-file", default="artifacts/issues.json", help="Path to issues.json"
    )
    parser.add_argument(
        "--output", default="artifacts/final_report.json", help="Output report path"
    )
    parser.add_argument(
        "--create-pr", action="store_true", help="Create GitHub PR for generated patch"
    )

    args = parser.parse_args()

    try:
        # Step 1: Load top issue
        print("Loading top-ranked issue from discovery...")
        issue = load_top_issue(args.issues_file)

        print(f"Selected Issue #{issue['issue_number']}: {issue['title']}")
        print(f"Priority Score: {issue['triage_data'].get('priority_score')}")
        print(f"Complexity: {issue['triage_data'].get('estimated_complexity_score')}")

        # Determine repo URL
        if args.repo_url:
            repo_url = args.repo_url
        else:
            # Try to infer from discovery or use placeholder
            repo_url = (
                "https://github.com/monkeytypegame/monkeytype-bot"  # Default for now
            )

        # Step 2: Run E2E pipeline
        e2e_result = run_e2e_pipeline(repo_url, issue["issue_number"])

        # Step 3: Generate final report
        report = generate_final_report(issue, e2e_result, args.output)

        # Step 4: Create PR if requested and patch was generated
        pr_url = None
        if args.create_pr and report["pipeline_result"]["patch_generated"]:
            print("\n" + "=" * 60)
            print("Creating GitHub Pull Request...")
            print("=" * 60)

            try:
                pr_creator = PRCreator(repo_url)

                # Get repo directory from run (use temp directory)
                import tempfile

                with tempfile.TemporaryDirectory() as repo_dir:
                    # Clone repo
                    import subprocess

                    subprocess.run(["git", "clone", repo_url, repo_dir], check=True)

                    # Create PR
                    pr_url = pr_creator.create_pr(
                        {
                            "issue_number": issue["issue_number"],
                            "patch_path": report["pipeline_result"]["patch_path"],
                            "confidence_score": report["confidence"][
                                "confidence_score"
                            ],
                            "risk_rating": report["confidence"]["risk_rating"],
                            "artifacts_dir": report["pipeline_result"].get(
                                "artifacts_dir", ""
                            ),
                            "repair_attempts": report["pipeline_result"][
                                "repair_attempts"
                            ],
                            "validation_passed": report["pipeline_result"][
                                "validation_passed"
                            ],
                        },
                        repo_dir,
                    )

                if pr_url:
                    print(f"✓ PR Created: {pr_url}")
                    report["pr_url"] = pr_url
                else:
                    print("✗ Failed to create PR")
            except Exception as e:
                print(f"Error creating PR: {e}")

        # Step 5: Print summary
        print("\n" + "=" * 60)
        print("AUTOMATION SUMMARY")
        print("=" * 60)
        print(f"Issue: #{report['issue']['issue_number']} - {report['issue']['title']}")
        print(f"Status: {report['summary']['status']}")
        print(
            f"Patch Generated: {'✓' if report['pipeline_result']['patch_generated'] else '✗'}"
        )
        print(
            f"Validation Passed: {'✓' if report['pipeline_result']['validation_passed'] else '✗'}"
        )
        print(f"Repair Attempts: {report['pipeline_result']['repair_attempts']}")
        print(
            f"\nConfidence: {report['confidence']['confidence_score']}/100 ({report['confidence']['risk_rating']} risk)"
        )
        print(f"Recommendation: {report['summary']['recommendation']}")
        if report["pipeline_result"]["patch_path"]:
            print(f"Patch: {report['pipeline_result']['patch_path']}")
        if pr_url:
            print(f"PR: {pr_url}")
        print("=" * 60)

        # Return summary as JSON (for programmatic use)
        summary_json = {
            "issue_number": report["issue"]["issue_number"],
            "patch_generated": report["pipeline_result"]["patch_generated"],
            "validation_passed": report["pipeline_result"]["validation_passed"],
            "repair_attempts": report["pipeline_result"]["repair_attempts"],
            "confidence_score": report["confidence"]["confidence_score"],
            "risk_rating": report["confidence"]["risk_rating"],
            "pr_url": pr_url,
            "artifacts_dir": report["pipeline_result"].get("artifacts_dir"),
        }

        print("\nSummary JSON:")
        print(json.dumps(summary_json, indent=2))

        # Exit with appropriate code
        sys.exit(0 if e2e_result["success"] else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
