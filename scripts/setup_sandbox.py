#!/usr/bin/env python3
"""Sandbox setup script for OpenFix testing.

Creates a sandbox repository with:
- Demo code files
- A test issue
- A lightweight bug for the agent to fix
"""
import os
import sys
import json
import subprocess
from pathlib import Path


def create_sandbox_repo(repo_path: str = "openfix-sandbox"):
    """Create a sandbox repository for testing."""
    repo_dir = Path(repo_path)

    if repo_dir.exists():
        print(f"⚠️  Directory {repo_path} already exists.")
        response = input("Delete and recreate? (y/n): ")
        if response.lower() != "y":
            return
        import shutil

        shutil.rmtree(repo_dir)

    # Create directory
    repo_dir.mkdir(parents=True)
    os.chdir(repo_dir)

    print(f"📁 Creating sandbox repository in {repo_dir.absolute()}...")

    # Initialize git
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.name", "OpenFix Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "openfix@example.com"], check=True)

    # Create demo files with a bug
    create_demo_files()

    # Commit
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit with demo code"], check=True)

    print("\n✅ Sandbox repository created!")
    print(f"\n📍 Location: {repo_dir.absolute()}")
    print("\n🔧 Next steps:")
    print("1. Create a GitHub repository:")
    print("   gh repo create openfix-sandbox --public --source=. --remote=origin")
    print("\n2. Push code:")
    print("   git push -u origin master")
    print("\n3. Create a test issue:")
    print("   gh issue create --title 'Calculator division by zero bug' \\")
    print(
        "     --body 'The calculator does not handle division by zero. This causes crashes.'"
    )
    print("\n4. Label the issue:")
    print("   gh issue edit 1 --add-label bug,openfix")
    print("\n5. Run OpenFix:")
    print(
        "   python scripts/automate_full_pipeline.py --repo-url https://github.com/YOUR_USERNAME/openfix-sandbox"
    )


def create_demo_files():
    """Create demo code files with bugs."""

    # Create README
    with open("README.md", "w") as f:
        f.write(
            """# OpenFix Sandbox

This is a test repository for OpenFix AI issue solver.

## Issues

This repository contains intentional bugs for testing:
1. Division by zero in calculator.py
2. Missing null check in user_manager.py

## Testing

OpenFix should be able to detect and fix these issues automatically.
"""
        )

    # Create calculator with division by zero bug
    with open("calculator.py", "w") as f:
        f.write(
            """#!/usr/bin/env python3
\"\"\"Simple calculator with a division by zero bug.\"\"\"

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    # BUG: No check for division by zero!
    return a / b

def main():
    print("Calculator Demo")
    print(f"10 + 5 = {add(10, 5)}")
    print(f"10 - 5 = {subtract(10, 5)}")
    print(f"10 * 5 = {multiply(10, 5)}")
    print(f"10 / 5 = {divide(10, 5)}")
    
    # This will crash!
    print(f"10 / 0 = {divide(10, 0)}")

if __name__ == "__main__":
    main()
"""
        )

    # Create user manager with null check bug
    with open("user_manager.py", "w") as f:
        f.write(
            """#!/usr/bin/env python3
\"\"\"User management with a null/None check bug.\"\"\"

class UserManager:
    def __init__(self):
        self.users = {}
    
    def add_user(self, user_id, name):
        self.users[user_id] = {"name": name}
    
    def get_user_name(self, user_id):
        # BUG: No check if user exists!
        return self.users[user_id]["name"]
    
    def display_user(self, user_id):
        name = self.get_user_name(user_id)
        print(f"User {user_id}: {name}")

def main():
    manager = UserManager()
    manager.add_user(1, "Alice")
    manager.add_user(2, "Bob")
    
    manager.display_user(1)
    manager.display_user(2)
    
    # This will crash!
    manager.display_user(999)

if __name__ == "__main__":
    main()
"""
        )

    # Create test file
    with open("test_calculator.py", "w") as f:
        f.write(
            """#!/usr/bin/env python3
\"\"\"Tests for calculator.\"\"\"
import unittest
from calculator import add, subtract, multiply, divide

class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(5, 3), 8)
    
    def test_subtract(self):
        self.assertEqual(subtract(5, 3), 2)
    
    def test_multiply(self):
        self.assertEqual(multiply(5, 3), 15)
    
    def test_divide(self):
        self.assertEqual(divide(10, 2), 5)
    
    def test_divide_by_zero(self):
        # This test should pass after the bug is fixed
        with self.assertRaises(ZeroDivisionError):
            divide(10, 0)

if __name__ == "__main__":
    unittest.main()
"""
        )

    # Create .gitignore
    with open(".gitignore", "w") as f:
        f.write(
            """__pycache__/
*.pyc
.env
venv/
.vscode/
"""
        )

    print("✅ Demo files created:")
    print("  - README.md")
    print("  - calculator.py (contains division by zero bug)")
    print("  - user_manager.py (contains null check bug)")
    print("  - test_calculator.py")


def check_issues_enabled(repo_url: str) -> bool:
    """Check if issues are enabled for a repository."""
    try:
        from github import Github
        import os

        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("⚠️  GITHUB_TOKEN not found in environment")
            return False

        gh = Github(token)

        # Extract owner/repo from URL
        parts = repo_url.rstrip("/").split("/")
        repo_name = f"{parts[-2]}/{parts[-1]}"

        repo = gh.get_repo(repo_name)

        if not repo.has_issues:
            print(f"\n❌ Issues are DISABLED for {repo_url}")
            print("\n🔧 To enable issues:")
            print("1. Go to repository Settings")
            print("2. Scroll to 'Features' section")
            print("3. Check the 'Issues' checkbox")
            print("4. Save changes")
            return False

        print(f"✅ Issues are enabled for {repo_url}")
        return True

    except Exception as e:
        print(f"⚠️  Could not check issue status: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup OpenFix sandbox repository")
    parser.add_argument(
        "--path", default="openfix-sandbox", help="Path for sandbox repo"
    )
    parser.add_argument("--check-issues", help="Check if issues are enabled for a repo")

    args = parser.parse_args()

    if args.check_issues:
        check_issues_enabled(args.check_issues)
    else:
        create_sandbox_repo(args.path)
