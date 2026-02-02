#!/usr/bin/env python3
"""
Test DeepSeek API connection
"""

import os
import sys
import httpx

# Set API Key from argument or environment
if len(sys.argv) > 1:
    DEEPSEEK_API_KEY = sys.argv[1]
else:
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

if not DEEPSEEK_API_KEY:
    print("Please set DEEPSEEK_API_KEY environment variable or pass as argument")
    print("Usage: python test_deepseek.py <api-key>")
    sys.exit(1)

print(f"API Key: {DEEPSEEK_API_KEY[:8]}...")

# Test connection
url = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json",
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello, introduce yourself briefly"}],
    "max_tokens": 100,
    "temperature": 0.7,
}

print("Testing DeepSeek API...")

try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        print("API connection successful!")
        print(f"\nResponse: {content}")

except httpx.HTTPStatusError as e:
    print(f"API request failed: {e.response.status_code}")
    print(f"Error: {e.response.text}")
    sys.exit(1)
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)
