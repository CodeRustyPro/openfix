#!/bin/bash
# Usage: ./validate_patch.sh --run-id <id> --task-id <id> --repo-dir <path> --patch <path> [--allow-network]
#
# Validates an AI-generated patch by applying it, running tests and linters.
# Produces validation.json with verdict: pass/fail/inconclusive

set -euo pipefail

# Parse arguments
RUN_ID=""
TASK_ID=""
REPO_DIR=""
PATCH_FILE=""
ALLOW_NETWORK=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --run-id) RUN_ID="$2"; shift 2 ;;
        --task-id) TASK_ID="$2"; shift 2 ;;
        --repo-dir) REPO_DIR="$2"; shift 2 ;;
        --patch) PATCH_FILE="$2"; shift 2 ;;
        --allow-network) ALLOW_NETWORK=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate required args
if [[ -z "$RUN_ID" ]] || [[ -z "$TASK_ID" ]] || [[ -z "$REPO_DIR" ]] || [[ -z "$PATCH_FILE" ]]; then
    echo "Error: Missing required arguments"
    echo "Usage: $0 --run-id <id> --task-id <id> --repo-dir <path> --patch <path>"
    exit 1
fi

# Setup paths
VALIDATION_DIR="/workspace/data/runs/$RUN_ID"
mkdir -p "$VALIDATION_DIR"
STDOUT_LOG="$VALIDATION_DIR/validation_stdout.log"
STDERR_LOG="$VALIDATION_DIR/validation_stderr.log"
VALIDATION_JSON="$VALIDATION_DIR/validation.json"

START_TIME=$(date +%s)

# Initialize result vars
APPLY_RESULT="unknown"
TESTS_RUN=()
TESTS_PASSED=0
TESTS_FAILED=0
LINTER_ISSUES=0
VERDICT="inconclusive"

# Change to repo directory  
cd "$REPO_DIR" || { echo "Error: Cannot cd to $REPO_DIR"; exit 1; }

# Detect language
detect_language() {
    if [[ -f "package.json" ]]; then
        echo "typescript"
    elif [[ -f "setup.py" ]] || [[ -f "pyproject.toml" ]] || [[ -f "requirements.txt" ]]; then
        echo "python"
    else
        echo "unknown"
    fi
}

LANGUAGE=$(detect_language)

# Apply patch
echo "Applying patch from $PATCH_FILE..." | tee -a "$STDOUT_LOG"
git checkout -b "ai-validation-$RUN_ID" >> "$STDOUT_LOG" 2>> "$STDERR_LOG" || true

if git apply --check "$PATCH_FILE" >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
    git apply "$PATCH_FILE" >> "$STDOUT_LOG" 2>> "$STDERR_LOG"
    APPLY_RESULT="success"
    echo "Patch applied successfully" | tee -a "$STDOUT_LOG"
else
    APPLY_RESULT="failed"
    echo "Patch application failed" | tee -a "$STDERR_LOG"
    VERDICT="fail"
fi

# If patch didn't apply,  exit early
if [[ "$APPLY_RESULT" != "success" ]]; then
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    cat > "$VALIDATION_JSON" <<EOF
{
  "run_id": "$RUN_ID",
  "task_id": "$TASK_ID",
  "applied_patch_path": "$PATCH_FILE",
  "apply_result": "$APPLY_RESULT",
  "tests_run": [],
  "tests_passed": 0,
  "tests_failed": 0,
  "linter_issues": 0,
  "stdout_log_path": "$STDOUT_LOG",
  "stderr_log_path": "$STDERR_LOG",
  "elapsed_seconds": $ELAPSED,
  "confidence_score": 0,
  "verdict": "$VERDICT"
}
EOF
    exit 1
fi

# Get modified files
MODIFIED_FILES=$(git diff --name-only HEAD)
echo "Modified files: $MODIFIED_FILES" | tee -a "$STDOUT_LOG"

# Run linters
run_linters() {
    local issues=0
    
    if [[ "$LANGUAGE" == "typescript" ]]; then
        echo "Running ESLint..." | tee -a "$STDOUT_LOG"
        if command -v eslint &> /dev/null; then
            if ! timeout 60 eslint $MODIFIED_FILES >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
                issues=$((issues + $(grep -c "error" "$STDERR_LOG" 2>/dev/null || echo 0)))
            fi
        fi
    elif [[ "$LANGUAGE" == "python" ]]; then
        echo "Running flake8..." | tee -a "$STDOUT_LOG"
        if command -v flake8 &> /dev/null; then
            if ! timeout 60 flake8 $MODIFIED_FILES >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
                issues=$((issues + $(wc -l < "$STDERR_LOG" 2>/dev/null || echo 0)))
            fi
        fi
    fi
    
    echo "$issues"
}

LINTER_ISSUES=$(run_linters)

# Run tests
run_tests() {
    local passed=0
    local failed=0
    
    if [[ "$LANGUAGE" == "typescript" ]] && [[ -f "package.json" ]]; then
        echo "Running npm test..." | tee -a "$STDOUT_LOG"
        if grep -q "\"test\"" package.json; then
            if timeout 120 npm test >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
                passed=1
                TESTS_RUN+=("npm test")
            else
                failed=1
                TESTS_RUN+=("npm test [FAILED]")
            fi
        fi
    elif [[ "$LANGUAGE" == "python" ]]; then
        echo "Running pytest..." | tee -a "$STDOUT_LOG"
        if command -v pytest &> /dev/null; then
            # Find test files related to modified files
            for file in $MODIFIED_FILES; do
                test_file=$(echo "$file" | sed 's/\.py$//')
                test_file="tests/test_${test_file##*/}.py"
                if [[ -f "$test_file" ]]; then
                    if timeout 120 pytest "$test_file" -v >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
                        passed=$((passed + 1))
                        TESTS_RUN+=("$test_file [PASS]")
                    else
                        failed=$((failed + 1))
                        TESTS_RUN+=("$test_file [FAIL]")
                    fi
                fi
            done
            
            # If no specific tests, run all
            if [[ ${#TESTS_RUN[@]} -eq 0 ]]; then
                if timeout 120 pytest -v >> "$STDOUT_LOG" 2>> "$STDERR_LOG"; then
                    passed=1
                    TESTS_RUN+=("pytest (all)")
                else
                    failed=1
                    TESTS_RUN+=("pytest (all) [FAILED]")
                fi
            fi
        fi
    fi
    
    TESTS_PASSED=$passed
    TESTS_FAILED=$failed
}

run_tests

# Compute verdict
if [[ $TESTS_FAILED -gt 0 ]] || [[ $LINTER_ISSUES -gt 10 ]]; then
    VERDICT="fail"
elif [[ $TESTS_PASSED -gt 0 ]] && [[ $LINTER_ISSUES -lt 5 ]]; then
    VERDICT="pass"
else
    VERDICT="inconclusive"
fi

# Compute confidence score
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

CONFIDENCE_SCORE=$(python3 /usr/local/bin/report_confidence.py \
    --tests-passed "$TESTS_PASSED" \
    --tests-failed "$TESTS_FAILED" \
    --linter-issues "$LINTER_ISSUES")

# Write validation.json
TESTS_JSON=$(printf '%s\n' "${TESTS_RUN[@]}" | jq -R . | jq -s .)

cat > "$VALIDATION_JSON" <<EOF
{
  "run_id": "$RUN_ID",
  "task_id": "$TASK_ID",
  "applied_patch_path": "$PATCH_FILE",
  "apply_result": "$APPLY_RESULT",
  "tests_run": $TESTS_JSON,
  "tests_passed": $TESTS_PASSED,
  "tests_failed": $TESTS_FAILED,
  "linter_issues": $LINTER_ISSUES,
  "stdout_log_path": "$STDOUT_LOG",
  "stderr_log_path": "$STDERR_LOG",
  "elapsed_seconds": $ELAPSED,
  "confidence_score": $CONFIDENCE_SCORE,
  "verdict": "$VERDICT"
}
EOF

echo "Validation complete. Verdict: $VERDICT"
cat "$VALIDATION_JSON"

# Exit 0 only if pass
[[ "$VERDICT" == "pass" ]] && exit 0 || exit 1
