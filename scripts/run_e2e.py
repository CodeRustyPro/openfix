#!/usr/bin/env python3
"""E2E test runner for OpenFix."""
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.solver.solver_agent import SolverAgent
from infrastructure.database.db import Database
from infrastructure.utils.logging import setup_logger

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
        # Initialize database and agent
        db = Database()
        solver = SolverAgent(config_path=args.config, db=db)

        # Execute pipeline
        result = solver.execute(repo_url=args.repo)

        # Report results
        logger.info("=" * 60)
        logger.info("OpenFix E2E Run Complete")
        logger.info("=" * 60)
        logger.info(f"Run ID: {solver.run_id}")

        validation_passed = result.get("validation_output", {}).get("passed", False)

        if result.get("success"):
            logger.info(f"✓ Patch generated: {result['patch_path']}")

            if validation_passed:
                logger.info("✓ Validation: PASSED")
            else:
                logger.warning("✓ Validation: FAILED")

            # Check if this is a success despite validation failure
            if not validation_passed and result.get("patch_path"):
                logger.warning("Warning: Patch generated but failed validation.")

            sys.exit(0)
        else:
            logger.error("✗ No patch generated")
            if result.get("error"):
                logger.error(f"Error: {result.get('error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db:
            db.close()


if __name__ == "__main__":

    args = parser.parse_args()

    run_e2e(args.repo, args.issue, args.config)
