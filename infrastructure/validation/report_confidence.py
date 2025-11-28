#!/usr/bin/env python3
"""Compute confidence score for patch validation.

Score algorithm:
- Test pass rate: 0-60 points (60 * pass_rate)
- Linter cleanliness: 0-30 points (30 - min(linter_issues, 30))
- Basic validation: 10 points if patch applied
"""

import argparse
import sys

def compute_confidence(tests_passed, tests_failed, linter_issues):
    """Compute confidence score 0-100."""
    score = 0
    
    # Test pass rate (60 points max)
    total_tests = tests_passed + tests_failed
    if total_tests > 0:
        pass_rate = tests_passed / total_tests
        score += int(60 * pass_rate)
    else:
        # No tests = moderate confidence
        score += 30
    
    # Linter cleanliness (30 points max)
    linter_penalty = min(linter_issues, 30)
    score += (30 - linter_penalty)
    
    # Patch applied successfully (10 points)
    score += 10
    
    return min(100, max(0, score))

def main():
    parser = argparse.ArgumentParser(description='Compute validation confidence score')
    parser.add_argument('--tests-passed', type=int, required=True)
    parser.add_argument('--tests-failed', type=int, required=True)
    parser.add_argument('--linter-issues', type=int, required=True)
    
    args = parser.parse_args()
    
    score = compute_confidence(args.tests_passed, args.tests_failed, args.linter_issues)
    print(score)
    return 0

if __name__ == '__main__':
    sys.exit(main())
