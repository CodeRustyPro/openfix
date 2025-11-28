"""Main CLI entry point for OpenFix."""
import sys
import argparse
import yaml
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.solver.solver_agent import SolverAgent
from data.database import Database


def load_config(config_path: str = "config/config.yml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="OpenFix - AI GitHub Issue Solver")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--issue", type=int, help="Specific issue number to solve")
    parser.add_argument("--config", default="config/config.yml", help="Path to config file")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    config['repo_url'] = args.repo_url
    if args.issue:
        config['issue_number'] = args.issue
    
    # Initialize database
    db = Database(config['db_path'])
    
    try:
        # Run solver agent
        solver = SolverAgent(config, db)
        result = solver.execute(args.repo_url)
        
        print("\n" + "="*60)
        print("OpenFix Run Complete")
        print("="*60)
        print(f"Run ID: {solver.run_id}")
        print(f"Repository: {args.repo_url}")
        if result.get('patch_generated'):
            print(f"✓ Patch generated: {result['patch_path']}")
            print(f"✓ Validation: {'PASSED' if result.get('validation_passed') else 'FAILED'}")
        else:
            print("✗ No patch generated")
            if result.get('error'):
                print(f"Error: {result['error']}")
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
