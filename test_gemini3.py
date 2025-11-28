"""Quick test to verify Gemini 3 Pro access with minimal tokens."""
import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

genai.configure(api_key=api_key)

# Test with gemini-3-pro-preview
print("Testing gemini-3-pro-preview...")
try:
    model = genai.GenerativeModel("gemini-3-pro-preview")
    response = model.generate_content("Say hello")
    print(f"✓ Success: {response.text}")
    print(f"Tokens: {response.usage_metadata.prompt_token_count} input, {response.usage_metadata.candidates_token_count} output")
except Exception as e:
    print(f"✗ Error: {e}")
