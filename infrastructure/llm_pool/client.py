"""LLM client with strict diff generation, artifact logging, and rate limiting."""
import os
import json
import time
from pathlib import Path
from datetime import datetime
from collections import deque
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class RateLimiter:
    """Simple token-based rate limiter for Gemini API."""
    
    def __init__(self, tokens_per_minute=900000):  # 900k to leave safety margin
        """
        Initialize rate limiter.
        
        Args:
            tokens_per_minute: Maximum tokens allowed per minute (default 900k for safety)
        """
        self.tokens_per_minute = tokens_per_minute
        self.token_history = deque()  # (timestamp, token_count) tuples
    
    def wait_if_needed(self, estimated_tokens, logger=None):
        """
        Sleep if needed to respect rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the upcoming request
            logger: Optional logger for transparency
        """
        now = time.time()
        
        # Remove entries older than 60 seconds
        while self.token_history and (now - self.token_history[0][0]) > 60:
            self.token_history.popleft()
        
        # Calculate tokens used in last 60 seconds
        tokens_in_window = sum(count for _, count in self.token_history)
        
        # Check if adding this request would exceed quota
        projected_total = tokens_in_window + estimated_tokens
        
        if projected_total > self.tokens_per_minute:
            # Calculate sleep time - wait until oldest entry expires
            if self.token_history:
                oldest_timestamp = self.token_history[0][0]
                sleep_time = max(0, 60 - (now - oldest_timestamp)) + 1  # +1 for safety
                
                if logger:
                    logger.info(f"⏱️  Rate limit approaching: {tokens_in_window}/{self.tokens_per_minute} tokens used")
                    logger.info(f"   Sleeping {sleep_time:.1f}s to respect quota...")
                else:
                    print(f"Rate limiting: sleeping {sleep_time:.1f}s...")
                
                time.sleep(sleep_time)
                
                # Clear old entries after sleeping
                now = time.time()
                while self.token_history and (now - self.token_history[0][0]) > 60:
                    self.token_history.popleft()
    
    def record_usage(self, token_count):
        """Record actual token usage after a successful request."""
        self.token_history.append((time.time(), token_count))


class GeminiLLM:
    """Gemini LLM client with artifact logging and rate limiting."""
    
    def __init__(self, model_name="gemini-3-pro-preview", logger=None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.rate_limiter = RateLimiter()
        self.logger = logger
    
    def generate_patch(self, issue_text: str, chunks: list, repo_name: str, 
                      issue_number: int, artifacts_dir: Path, validation_results: str = "None") -> dict:
        """
        Generate a git patch for an issue.
        
        Args:
            issue_text: Combined issue title and body
            chunks: List of CodeChunk objects with relevant code
            repo_name: Repository name
            issue_number: Issue number
            artifacts_dir: Directory to save artifacts
            validation_results: Output from previous validation run (optional)
            
        Returns:
            Dict with 'success', 'diff', 'reason', 'prompt_tokens', 'response_tokens'
        """
        # Build prompt
        prompt = self._build_patch_prompt(issue_text, chunks, repo_name, issue_number, validation_results)
        
        # Estimate tokens (rough: 4 chars = 1 token)
        estimated_tokens = len(prompt) // 4
        
        if self.logger:
            self.logger.info(f"Estimated tokens: ~{estimated_tokens:,}")
        
        # Wait if needed to respect rate limits
        self.rate_limiter.wait_if_needed(estimated_tokens, self.logger)
        
        # Save prompt
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / 'prompt.txt', 'w') as f:
            f.write(prompt)
        
        # Call Gemini
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract token counts
            prompt_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else estimated_tokens
            response_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
            
            # Record actual usage
            self.rate_limiter.record_usage(prompt_tokens + response_tokens)
            
            if self.logger:
                self.logger.info(f"✓ LLM response received: {prompt_tokens:,} input + {response_tokens:,} output tokens")
            
            # Save response
            response_data = {
                'model': self.model_name,
                'timestamp': datetime.utcnow().isoformat(),
                'prompt_tokens': prompt_tokens,
                'response_tokens': response_tokens,
                'response_text': response_text
            }
            
            with open(artifacts_dir / 'response.json', 'w') as f:
                json.dump(response_data, f, indent=2)
            
            # Parse response
            patch_content = None
            reason = None
            
            try:
                # Extract JSON block
                text = response_text
                if "```json" in text:
                    start = text.find("```json") + 7
                    end = text.find("```", start)
                    if end != -1:
                        text = text[start:end]
                elif "```" in text: # Maybe just ``` without json
                    start = text.find("```") + 3
                    end = text.find("```", start)
                    if end != -1:
                        text = text[start:end]
                
                # If still has preamble, try to find first { and last }
                if not text.strip().startswith("{"):
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1:
                        text = text[start:end+1]

                patch_data = json.loads(text.strip())
                patch_content = patch_data.get("patch_text", "")
                explanation = patch_data.get("explanation", "")
                risk = patch_data.get("estimated_risk", "Unknown")
                
                if self.logger:
                    self.logger.info(f"Patch generated. Explanation: {explanation} (Risk: {risk})")
            except (json.JSONDecodeError, AttributeError, ValueError):
                if self.logger:
                    self.logger.warning("Failed to parse LLM JSON response. Fallback to raw text parsing.")
                patch_content = response_text

            if not patch_content:
                 return {
                    'success': False,
                    'diff': None,
                    'reason': "Empty patch content",
                    'prompt_tokens': prompt_tokens,
                    'response_tokens': response_tokens
                }

            if 'CANNOT_FIX_SAFELY' in patch_content:
                reason = patch_content.split('CANNOT_FIX_SAFELY:', 1)[1].strip() if ':' in patch_content else patch_content
                return {
                    'success': False,
                    'diff': None,
                    'reason': reason,
                    'prompt_tokens': prompt_tokens,
                    'response_tokens': response_tokens
                }
            
            # Extract diff (look for --- and +++ markers) if not already clean
            if '---' in patch_content and '+++' in patch_content:
                 return {
                    'success': True,
                    'diff': patch_content,
                    'reason': None,
                    'prompt_tokens': prompt_tokens,
                    'response_tokens': response_tokens
                }
            else:
                return {
                    'success': False,
                    'diff': None,
                    'reason': 'LLM did not output valid diff format in JSON',
                    'prompt_tokens': prompt_tokens,
                    'response_tokens': response_tokens
                }
                
        except Exception as e:
            # Save error
            with open(artifacts_dir / 'error.txt', 'w') as f:
                f.write(f"Error: {str(e)}\n")
            
            return {
                'success': False,
                'diff': None,
                'reason': f'LLM call failed: {str(e)}',
                'prompt_tokens': 0,
                'response_tokens': 0
            }
    
    def _build_patch_prompt(self, issue_text: str, chunks: list, repo_name: str, 
                           issue_number: int, validation_results: str = "None") -> str:
        """Build the patch generation prompt."""
        
        # Format chunks
        chunks_text = ""
        for i, chunk in enumerate(chunks, 1):
            chunks_text += f"\n### Chunk {i}: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n"
            chunks_text += f"```\n{chunk.content}\n```\n"
        
        try:
            with open("infrastructure/prompts/patchbuilder_json_prompt.txt", "r") as f:
                prompt_tmpl = f.read()
                
            prompt = prompt_tmpl.format(
                REPO_URL=repo_name,
                ISSUE_NUMBER=issue_number,
                ISSUE_DESCRIPTION=issue_text,
                CONTEXT_CHUNKS=chunks_text,
                METRICS="N/A",
                EXISTING_PATCH="None",
                VALIDATION_RESULTS=validation_results
            )
            return prompt
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load prompt template: {e}")
            # Fallback to hardcoded if file missing
            return f"Error loading prompt: {e}"
    def triage_issue(self, issue_title: str, issue_body: str, labels: list) -> dict:
        """
        Analyze an issue to determine suitability for automation.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            labels: List of label names
            
        Returns:
            Dict with triage results (is_suitable, complexity, etc.)
        """
        try:
            # Load prompt
            with open("infrastructure/prompts/triage_prompt.txt", "r") as f:
                prompt_tmpl = f.read()
                
            prompt = prompt_tmpl.format(
                ISSUE_TITLE=issue_title,
                ISSUE_BODY=issue_body[:2000], # Truncate body to avoid huge context
                LABELS=", ".join(labels),
                ISSUE_NUMBER="0" # Placeholder
            )
            
            # Estimate tokens
            estimated_tokens = len(prompt) // 4
            self.rate_limiter.wait_if_needed(estimated_tokens, self.logger)
            
            # Generate
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Record usage
            prompt_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else estimated_tokens
            response_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
            self.rate_limiter.record_usage(prompt_tokens + response_tokens)
            
            # Parse JSON
            try:
                text = response_text
                if "```json" in text:
                    start = text.find("```json") + 7
                    end = text.find("```", start)
                    if end != -1:
                        text = text[start:end]
                elif "```" in text:
                    start = text.find("```") + 3
                    end = text.find("```", start)
                    if end != -1:
                        text = text[start:end]
                
                if not text.strip().startswith("{"):
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                        
                return json.loads(text.strip())
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to parse triage JSON: {e}")
                return {
                    "is_suitable": False,
                    "reason": f"Failed to parse LLM response: {e}",
                    "estimated_complexity_score": "unknown",
                    "priority_score": 0
                }
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Triage failed: {e}")
            return {
                "is_suitable": False,
                "reason": f"LLM call failed: {e}",
                "estimated_complexity_score": "unknown",
                "priority_score": 0
            }
