# OpenFix Architecture Guide

This document explains how the **OpenFix Agent** works, breaking down its structure and the step-by-step flow of how it autonomously solves GitHub issues.

## 1. High-Level Overview

OpenFix is an autonomous agent that:
1.  **Ingests** a GitHub repository.
2.  **Reads** an issue description.
3.  **Finds** relevant code.
4.  **Generates** a patch using Gemini.
5.  **Validates** the patch (optional).

It is built in Python and uses a modular architecture.

---

## 2. Directory Structure

Here are the key components you need to know:

```
openfix/
├── agents/                 # The "Brain" of the system
│   ├── solver/             # Core logic for solving issues
│   │   └── solver_agent.py # Main orchestrator
│   └── base_agent.py       # Shared agent functionality
│
├── infrastructure/         # The "Tools" used by the agent
│   ├── llm_pool/           # LLM Client (Gemini API)
│   ├── code_graph/         # Code ingestion & chunking
│   ├── git/                # GitHub API interaction
│   └── validation/         # Scripts to test patches
│
├── data/                   # The "Memory"
│   ├── db/                 # SQLite database (openfix.db)
│   └── patches/            # Generated patch files
│
├── config/                 # Configuration
│   └── config.yml          # Settings (models, limits, paths)
│
└── scripts/                # Entry Points
    └── run_e2e.py          # Main script to run the agent
```

---

## 3. Step-by-Step Execution Flow

When you run `python scripts/run_e2e.py`, here is exactly what happens:

### Step 1: Initialization
- **Script:** `scripts/run_e2e.py`
- **Action:** Loads `config.yml`, connects to the SQLite database (`data/database.py`), and initializes the `SolverAgent`.

### Step 2: Ingestion
- **Component:** `infrastructure/code_graph/ingestion.py`
- **Action:**
    - Clones the target GitHub repository to a temporary folder.
    - Walks through all files, filtering out binaries and junk (like `node_modules`).
    - Creates a single text representation of the codebase.

### Step 3: Chunking & Retrieval
- **Component:** `infrastructure/code_graph/chunk_selector.py`
- **Action:**
    - Splits the huge codebase text into smaller "chunks" (e.g., functions or classes).
    - Compares these chunks to the Issue Title/Body.
    - Selects the **Top K** (default 10) most relevant chunks to send to the AI.

### Step 4: Reasoning (The "Brain")
- **Component:** `infrastructure/llm_pool/client.py`
- **Action:**
    - Constructs a prompt containing:
        1.  The Issue Description.
        2.  The Selected Code Chunks.
        3.  Instructions to generate a Git Patch.
    - Sends this to **Gemini Pro**.
    - Receives a JSON response containing the patch and an explanation.

### Step 5: Patch Generation
- **Component:** `agents/solver/solver_agent.py`
- **Action:**
    - Extracts the diff from the LLM response.
    - Saves it to `data/patches/issue-X/fix.patch`.
    - Updates the database with the run results.

### Step 6: Validation (Optional Loop)
- **Component:** `infrastructure/validation/validate_patch.sh`
- **Action:**
    - Tries to apply the patch.
    - Runs tests (if configured).
    - If validation fails, the agent can optionally feed the error back to Gemini to "repair" the patch (Self-Healing).

---

## 4. Key Technologies

- **Language:** Python 3.11+
- **Database:** SQLite (Simple, file-based)
- **AI Model:** Google Gemini Pro (via `google-generativeai` SDK)
- **VCS:** Git (via `GitPython`)

## 5. Why This Design?

- **Modular:** You can swap out the LLM or the Database without rewriting the agent.
- **Traceable:** Every run, token usage, and error is logged to the SQLite DB.
- **Safe:** Patches are generated in a separate folder, not directly applied to your main repo until you approve.
