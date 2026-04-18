#!/usr/bin/env python3
"""Test model names to find the correct one"""

import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
CREDS = BASE_DIR / "credentials.json"

creds = json.loads(CREDS.read_text())
ANTHROPIC_API_KEY = creds.get("anthropic_api_key", "")

HEADERS = {
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
    "x-api-key": ANTHROPIC_API_KEY
}

# Test different model names
models_to_test = [
    "claude-sonnet-4-6",
    "claude-sonnet-4-6-20250217", 
    "claude-sonnet-4.6",
    "claude-3-5-sonnet-20241022"  # fallback
]

for model in models_to_test:
    print(f"Testing model: {model}")
    
    payload = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✅ {model} - WORKS")
        break
    else:
        print(f"❌ {model} - Error {response.status_code}: {response.json().get('error', {}).get('message', 'Unknown')}")

print("Done")
