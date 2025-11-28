# Validation Harness - OpenFix Phase Zero

## Build Docker Image

```bash
cd /Users/dev/openfix
docker build -t ai-validation:phase0 -f infrastructure/validation/Dockerfile .
```

## Run Validation

### Example: Validate monkeytype-bot patch

```bash
# Clone the repo first
git clone https://github.com/monkeytypegame/monkeytype-bot /tmp/monkeytype-bot

# Run validation in Docker
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  ai-validation:phase0 \
  /usr/local/bin/validate_patch.sh \
    --run-id b9d2768a \
    --task-id t1 \
    --repo-dir /tmp/monkeytype-bot \
    --patch /workspace/data/patches/issue-81/fix.patch
```

### With network access (if needed for npm install, etc.)

```bash
docker run --rm \
  --network=host \
  -v "$(pwd)":/workspace \
  -w /workspace \
  ai-validation:phase0 \
  /usr/local/bin/validate_patch.sh \
    --run-id b9d2768a \
    --task-id t1 \
    --repo-dir /tmp/monkeytype-bot \
    --patch /workspace/data/patches/issue-81/fix.patch \
    --allow-network
```

## Inspect Results

```bash
cat data/runs/b9d2768a/validation.json | jq .
cat data/runs/b9d2768a/validation_stdout.log
cat data/runs/b9d2768a/validation_stderr.log
```

## Detected Failure Modes

The harness detects and reports:

1. **Patch Application Failures** - Git apply errors, merge conflicts, malformed diffs → `apply_result: "failed"`, `verdict: "fail"`

2. **Test Failures** - Any test that fails after patch application → recorded in `tests_failed`, lowers `confidence_score`

3. **Linter Violations** - ESLint/flake8 errors introduced by patch → counted in `linter_issues`, affects `verdict`

4. **Timeouts** - Tests/linters exceeding 120s limit → killed, counted as failures

5. **Missing Test Commands** - No `package.json` test script or pytest → `verdict: "inconclusive"`

6. **Resource Exhaustion** - OOM or CPU limit hit → logged to stderr, `verdict: "fail"`

7. **Network Failures** - Dependency install failures when network disabled → logged, suggests `--allow-network`

8. **Invalid Patch Format** - Non-unified diff or corrupted patch file → `apply_result: "failed"`

All failures are logged to stderr with full stacktraces for debugging.
