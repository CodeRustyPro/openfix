#!/usr/bin/env python3
"""E2E test runner for OpenFix."""
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.solver.solver_agent import SolverAgent
from data.database import Database
from infrastructure.utils.logging import setup_logger
import yaml

logger = setup_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="OpenFix E2E Test Runner")
    parser.add_argument("--repo", required=True, help="Repository URL")
    parser.add_argument("--issue", type=int, required=True, help="Issue number")
    parser.add_argument(
        "--config", default="config/config.yml", help="Config file path"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging with verbose mode
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Starting E2E Run for {args.repo} issue #{args.issue}")

    db = None  # Initialize db to None
    try:
        # Load config
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)

        # Initialize database and agent
        db = Database("data/db/openfix.db")
        solver = SolverAgent(config, db)
        
        # Override issue number in config if needed (though execute takes it from repo/issue)
        # Actually solver.execute takes repo_url. But how does it know which issue?
        # SolverAgent._select_issue uses config['issue_number'] if present.
        solver.config['issue_number'] = args.issue

        # Execute pipeline
        result = solver.execute(repo_url=args.repo)

        # Report results
        logger.info("=" * 60)
        logger.info("OpenFix E2E Run Complete")
        logger.info("=" * 60)
        logger.info(f"Run ID: {result.get('run_id')}")

        validation_passed = result.get("validation_passed", False)

        if result.get("patch_generated"):
            logger.info(f"✓ Patch generated: {result['patch_path']}")

            if validation_passed:
                logger.info("✓ Validation: PASSED")
            else:
                logger.warning("✓ Validation: FAILED")

            sys.exit(0)
        else:
            logger.error("✗ No patch generated")
            if result.get("reason"):
                logger.error(f"Reason: {result.get('reason')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
