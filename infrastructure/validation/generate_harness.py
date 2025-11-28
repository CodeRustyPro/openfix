#!/usr/bin/env python3
"""Generate validation harness using Gemini 2.5 Pro."""
import os
import sys
import google.generativeai as genai

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not set")
    sys.exit(1)

genai.configure(api_key=api_key)

# Read prompt
with open("infrastructure/validation/harness_prompt.txt", "r") as f:
    prompt = f.read()

# Call Gemini 2.5 Pro
model = genai.GenerativeModel("gemini-2.5-pro")
response = model.generate_content(
    prompt,
    generation_config=genai.GenerationConfig(
        temperature=0.0,
        max_output_tokens=8000
    )
)

# Output response
print(response.text)
