"""Multi-step repair orchestrator."""
import os
import json
import argparse
import logging
from pathlib import Path
import subprocess
from typing import Dict, Any

from infrastructure.retrieval.chunk_selector import ChunkSelector
from infrastructure.llm.llm_client import LLMClient
from infrastructure.metrics.metrics import Metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, repo_dir: str, run_id: str):
        self.repo_dir = repo_dir
        self.run_id = run_id
        self.artifacts_dir = Path(f"data/runs/{run_id}")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        self.chunk_selector = ChunkSelector(repo_dir)
        self.llm_client = LLMClient()
        self.metrics = Metrics()

    def run(self, issue_title: str, issue_body: str, max_retries: int = 3):
        logger.info(f"Starting repair for run {self.run_id}")
        
        # 1. Ingest & Retrieve
        logger.info("Ingesting codebase...")
        self.chunk_selector.ingest()
        
        query = f"{issue_title}\n{issue_body}"
        chunks = self.chunk_selector.query(query, top_k=5)
        
        context_str = "\n".join([
            f"File: {c.file_path}\nLines: {c.start_line}-{c.end_line}\n{c.content}\n"
            for c in chunks
        ])
        
        # 2. Initial Patch
        logger.info("Generating initial patch...")
        with open("infrastructure/prompts/patchbuilder_json_prompt.txt", "r") as f:
            prompt_tmpl = f.read()
            
        prompt = prompt_tmpl.format(
            REPO_URL=self.repo_dir, # Using repo_dir as URL proxy for now
            ISSUE_NUMBER=self.run_id, # Using run_id as issue number proxy
            CONTEXT_CHUNKS=context_str,
            METRICS="N/A"
        )
        
        response = self.llm_client.call_llm(prompt)
        
        try:
            # Clean JSON block
            text = response["text"].replace("```json", "").replace("```", "").strip()
            patch_data = json.loads(text)
            patch_content = patch_data.get("patch_text", "")
            explanation = patch_data.get("explanation", "")
            logger.info(f"Patch generated. Explanation: {explanation}")
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM JSON response. Fallback to raw text.")
            patch_content = response["text"]
            
        self.metrics.record_attempt(False, response["usage"]["total_tokens"])
        
        if "CANNOT_FIX_SAFELY" in patch_content:
            logger.warning("LLM declined to fix.")
            return self._finish("failed", "LLM declined")

        patch_path = self.artifacts_dir / "fix.patch"
        with open(patch_path, "w") as f:
            f.write(patch_content)

        # 3. Repair Loop
        for attempt in range(max_retries + 1):
            logger.info(f"Validation attempt {attempt+1}...")
            
            # Validate
            val_res = self._validate(patch_path)
            
            if val_res["verdict"] == "pass":
                logger.info("Patch passed validation!")
                self.metrics.record_attempt(True, 0)
                return self._finish("success", "Patch passed validation")
            
            if attempt == max_retries:
                logger.warning("Max retries reached.")
                break
                
            # Prepare repair
            logger.info("Patch failed. Attempting repair...")
            with open("infrastructure/prompts/repair_loop_prompt.txt", "r") as f:
                repair_tmpl = f.read()
            
            logs = ""
            if os.path.exists(val_res["stderr_log_path"]):
                with open(val_res["stderr_log_path"], "r") as f:
                    logs += f.read()
            
            repair_prompt = repair_tmpl.format(
                PREVIOUS_PATCH=patch_content,
                FAILURE_LOGS=logs[-2000:], # Truncate logs
                CONTEXT_CHUNKS=context_str
            )
            
            response = self.llm_client.call_llm(repair_prompt)
            patch_content = response["text"]
            self.metrics.record_attempt(False, response["usage"]["total_tokens"])
            
            with open(patch_path, "w") as f:
                f.write(patch_content)

        return self._finish("failed", "Max retries exceeded")

    def _validate(self, patch_path: Path) -> Dict[str, Any]:
        cmd = [
            "infrastructure/validation/validate_patch.sh",
            "--run-id", self.run_id,
            "--task-id", "repair",
            "--repo-dir", self.repo_dir,
            "--patch", str(patch_path)
        ]
        
        # We assume validate_patch.sh is available and executable
        # For this artifact, we mock the call if script missing, or call it if present
        if not os.path.exists(cmd[0]):
             logger.warning("Validation script not found, mocking fail.")
             return {"verdict": "fail", "stderr_log_path": "/dev/null"}

        try:
            subprocess.run(cmd, check=False, capture_output=True)
            # Read result json
            res_path = self.artifacts_dir / "validation.json"
            if res_path.exists():
                with open(res_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            
        return {"verdict": "fail", "stderr_log_path": "/dev/null"}

    def _finish(self, status: str, reason: str):
        self.metrics.save(self.artifacts_dir / "metrics.json")
        result = {
            "status": status,
            "reason": reason,
            "run_id": self.run_id,
            "metrics": self.metrics.get()
        }
        with open(self.artifacts_dir / "result.json", "w") as f:
            json.dump(result, f, indent=2)
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", required=True)
    parser.add_argument("--issue-title", default="Issue")
    parser.add_argument("--issue-body", default="")
    parser.add_argument("--run-id", default="test_run")
    args = parser.parse_args()
    
    orch = Orchestrator(args.repo_dir, args.run_id)
    res = orch.run(args.issue_title, args.issue_body)
    print(json.dumps(res, indent=2))
