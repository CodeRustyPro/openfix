# Phase 1 Quickstart

## Prerequisites
- Python 3.10+
- Docker
- `GEMINI_API_KEY` set
- `GITHUB_TOKEN` set

## Installation
```bash
pip install -r requirements.txt
pip install faiss-cpu sentence-transformers  # Optional for better retrieval
```

## Running E2E Test
Run the full repair loop on a public issue:

```bash
python3 scripts/run_e2e.py --repo https://github.com/monkeytypegame/monkeytype-bot --issue 81
```

## Issue Discovery
Find actionable issues in a repo:

```bash
python3 agents/discovery/discover_issues.py --org monkeytypegame --repo monkeytype-bot
```

## Inspecting Results
Artifacts are saved in `data/runs/<run_id>/`:
- `fix.patch`: The generated patch
- `validation.json`: Validation results
- `metrics.json`: Performance metrics
- `result.json`: Final status
