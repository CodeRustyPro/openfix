"""LLM client wrapper for Phase 1."""
import os
import logging
import google.generativeai as genai
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set")
        else:
            genai.configure(api_key=self.api_key)

    def call_llm(self, prompt: str, model: str = "gemini-2.5-pro", 
                 max_tokens: int = 8192, temperature: float = 0.0) -> Dict[str, Any]:
        """Call LLM and return response with token usage."""
        if not self.api_key:
            return {"text": "API_KEY_MISSING", "usage": {"prompt_tokens": 0, "completion_tokens": 0}}

        try:
            generative_model = genai.GenerativeModel(model)
            response = generative_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            
            # Estimate tokens if metadata missing (rough fallback)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response.text) // 4
            
            if hasattr(response, 'usage_metadata'):
                prompt_tokens = response.usage_metadata.prompt_token_count
                completion_tokens = response.usage_metadata.candidates_token_count

            return {
                "text": response.text,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"text": f"ERROR: {str(e)}", "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
