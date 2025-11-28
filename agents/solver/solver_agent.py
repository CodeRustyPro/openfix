"""Solver agent orchestrates the patch generation pipeline."""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.base_agent import BaseAgent
from infrastructure.code_graph.ingestion import Ingestor
from infrastructure.git.github_client import GitHubClient
from infrastructure.code_graph.chunk_selector import ChunkSelector
from infrastructure.llm_pool.client import GeminiLLM
from data.database import Database


class SolverAgent(BaseAgent):
    """Agent that solves GitHub issues by generating patches."""
    
    def __init__(self, config: Dict[str, Any], db: Database):
        """Initialize solver agent."""
        super().__init__(config)
        self.db = db
        self.ingestor = Ingestor()
        self.github_client = GitHubClient()
        self.chunk_selector = ChunkSelector(
            chunk_size=config.get('chunk_size', 500),
            overlap=config.get('overlap', 50)
        )
        self.llm = GeminiLLM(
            model_name=config.get('llm_model', 'gemini-3-pro-preview'),
            logger=self.logger
        )
    
    def execute(self, repo_url: str) -> Dict[str, Any]:
        """
        Execute the solver pipeline.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Dict with results including patch_path, validation results, etc.
        """
        try:
            self.logger.info(f"Starting solve pipeline for {repo_url}")
            
            # 1. Insert repository
            repo_name = repo_url.split('/')[-1]
            repo_id = self.db.insert_repository(repo_url, repo_name)
            
            # 2. Fetch issues
            self.logger.info("Fetching issues from GitHub...")
            issues = self.github_client.get_repo_issues(repo_url)
            
            if not issues:
                return {"error": "No issues found", "patch_generated": False}
            
            self.logger.info(f"Found {len(issues)} issues")
            
            # 3. Select issue to solve
            issue = self._select_issue(issues)
            issue_id = self.db.insert_issue(
                repo_id,
                issue.number,
                issue.title,
                issue.body or "",
                [label.name for label in issue.labels]
            )
            
            # 4. Create run
            run_db_id = self.db.insert_run(self.run_id, repo_id, issue_id)
            
            # 5. Ingest codebase
            self.logger.info("Ingesting codebase...")
            self.ingestor.clone_repo(repo_url)
            codebase_text = self.ingestor.get_codebase_context()
            
            # 6. Create chunks
            chunks = self._create_chunks(codebase_text)
            self.logger.info(f"Created {len(chunks)} code chunks")
            
            # 7. Select relevant chunks
            issue_text = f"{issue.title}\n\n{issue.body or ''}"
            selected_chunks = self.chunk_selector.select_chunks(
                chunks,
                issue_text,
                top_k=self.config.get('top_k_chunks', 10)
            )
            
            self.log_metric('chunks_selected', len(selected_chunks))
            self.logger.info(f"Selected {len(selected_chunks)} relevant chunks")
            
            # 8. Create artifacts directory
            artifacts_dir = Path(self.config['runs_dir']) / self.run_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # 9. Save selected chunks
            with open(artifacts_dir / 'chunks.json', 'w') as f:
                json.dump([{
                    'file': c.file_path,
                    'lines': f"{c.start_line}-{c.end_line}",
                    'score': c.relevance_score,
                    'content': c.content
                } for c in selected_chunks], f, indent=2)
            
            # 10. Save issue
            with open(artifacts_dir / 'issue.md', 'w') as f:
                f.write(f"# Issue #{issue.number}: {issue.title}\n\n{issue.body or ''}")
            
            # 11. Generate patch using LLM
            self.logger.info("Generating patch with LLM...")
            llm_result = self.llm.generate_patch(
                issue_text,
                selected_chunks,
                repo_name,
                issue.number,
                artifacts_dir
            )
            
            self.log_metric('prompt_tokens', llm_result['prompt_tokens'])
            self.log_metric('response_tokens', llm_result['response_tokens'])
            
            # 12. Handle result and Repair Loop
            max_retries = 1
            current_result = llm_result
            
            for attempt in range(max_retries + 1):
                if not current_result['success']:
                    self.logger.warning(f"Patch generation failed: {current_result['reason']}")
                    break # Cannot repair if generation failed completely
                
                # Save patch file
                patch_dir = Path(self.config['patch_dir']) / f"issue-{issue.number}"
                patch_dir.mkdir(parents=True, exist_ok=True)
                patch_path = patch_dir / "fix.patch"
                
                with open(patch_path, 'w') as f:
                    f.write(current_result['diff'])
                
                self.logger.info(f"Patch saved to {patch_path}")
                
                # Validate Patch
                validation_output = "No validation run."
                validation_passed = False
                
                # Run validation script
                import subprocess
                validate_cmd = [
                    "infrastructure/validation/validate_patch.sh",
                    "--run-id", self.run_id,
                    "--task-id", f"attempt-{attempt}",
                    "--repo-dir", str(Path(self.ingestor.temp_dir)), # Use ingested path
                    "--patch", str(patch_path)
                ]
                
                try:
                    self.logger.info(f"Validating patch (Attempt {attempt+1})...")
                    # Ensure script is executable
                    subprocess.run(["chmod", "+x", "infrastructure/validation/validate_patch.sh"], check=True)
                    
                    # Run validation
                    proc = subprocess.run(validate_cmd, capture_output=True, text=True)
                    validation_output = proc.stdout + "\n" + proc.stderr
                    
                    # Check validation.json
                    val_json_path = artifacts_dir / "validation.json"
                    if val_json_path.exists():
                        with open(val_json_path, 'r') as f:
                            val_data = json.load(f)
                            if val_data.get("verdict") == "pass":
                                validation_passed = True
                                self.logger.info("✓ Validation PASSED!")
                                break # Success!
                            else:
                                self.logger.warning(f"✗ Validation FAILED: {val_data.get('failure_reason')}")
                                validation_output = json.dumps(val_data, indent=2)
                    else:
                         self.logger.warning("Validation JSON not found.")

                except Exception as e:
                    self.logger.error(f"Validation execution failed: {e}")
                    validation_output = f"Validation execution error: {str(e)}"

                # If we are here, validation failed (or didn't run).
                # If we have retries left, try to repair.
                if attempt < max_retries:
                    self.logger.info("Attempting to repair patch with validation feedback...")
                    current_result = self.llm.generate_patch(
                        issue_text,
                        selected_chunks,
                        repo_name,
                        issue.number,
                        artifacts_dir,
                        validation_results=validation_output
                    )
                    
                    self.log_metric(f'repair_prompt_tokens_{attempt}', current_result['prompt_tokens'])
                    self.log_metric(f'repair_response_tokens_{attempt}', current_result['response_tokens'])
                else:
                    self.logger.warning("Max retries reached. Stopping.")

            # Final Result Handling
            if current_result['success']:
                 # Update database with final status
                status = 'SUCCESS' if validation_passed else 'GENERATED_BUT_FAILED_VALIDATION'
                
                self.db.insert_patch(
                    issue_id,
                    self.run_id,
                    current_result['diff'],
                    status=status
                )
                
                self.db.update_run(
                    self.run_id,
                    chunks_selected=len(selected_chunks),
                    prompt_tokens=current_result['prompt_tokens'], # Last run tokens
                    response_tokens=current_result['response_tokens'],
                    artifacts_path=str(artifacts_dir),
                    status=status
                )
                
                self.ingestor.cleanup()
                
                return {
                    'run_id': self.run_id,
                    'issue_number': issue.number,
                    'patch_generated': True,
                    'patch_path': str(patch_path),
                    'validation_passed': validation_passed,
                    'chunks_selected': len(selected_chunks),
                    'artifacts_dir': str(artifacts_dir),
                    'metrics': self.get_metrics()
                }
            else:
                # Failed
                self.logger.warning(f"Patch generation failed: {current_result['reason']}")
                
                self.db.update_run(
                    self.run_id,
                    chunks_selected=len(selected_chunks),
                    prompt_tokens=current_result['prompt_tokens'],
                    response_tokens=current_result['response_tokens'],
                    artifacts_path=str(artifacts_dir),
                    status='FAILED',
                    error_message=current_result['reason']
                )
                
                self.ingestor.cleanup()
                
                return {
                    'run_id': self.run_id,
                    'issue_number': issue.number,
                    'patch_generated': False,
                    'reason': current_result['reason'],
                    'artifacts_dir': str(artifacts_dir),
                    'metrics': self.get_metrics()
                }
            
        except Exception as e:
            self.logger.error(f"Error in solve pipeline: {e}", exc_info=True)
            self.db.update_run(self.run_id, status='FAILED', error_message=str(e))
            self.ingestor.cleanup()
            raise
    
    def _select_issue(self, issues):
        """Select which issue to solve."""
        # If specific issue number provided, use that
        if self.config.get('issue_number'):
            for issue in issues:
                if issue.number == self.config['issue_number']:
                    return issue
            raise ValueError(f"Issue #{self.config['issue_number']} not found")
        
        # Otherwise, pick first issue
        return issues[0]
    
    def _create_chunks(self, codebase_text: str):
        """Create chunks from ingested codebase."""
        from infrastructure.code_graph.chunk_selector import CodeChunk
        
        # Parse codebase text which has format: "--- FILE: path ---\ncontent"
        chunks = []
        current_file = None
        current_content = []
        
        for line in codebase_text.split('\n'):
            if line.startswith('--- FILE:'):
                # Save previous file if exists
                if current_file and current_content:
                    content = '\n'.join(current_content)
                    file_chunks = self.chunk_selector.chunk_file(current_file, content)
                    chunks.extend(file_chunks)
                
                # Start new file
                current_file = line.replace('--- FILE:', '').replace('---', '').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last file
        if current_file and current_content:
            content = '\n'.join(current_content)
            file_chunks = self.chunk_selector.chunk_file(current_file, content)
            chunks.extend(file_chunks)
        
        return chunks
