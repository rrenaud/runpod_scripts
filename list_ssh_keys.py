#!/usr/bin/env python3
"""List SSH keys registered with RunPod account."""

import json
import requests
from pathlib import Path

# Read API key
api_key = Path.home() / ".runpod_api_key.txt"
key = api_key.read_text().strip()

# GraphQL query to list SSH keys
query = """
query {
  myself {
    pubKey
  }
}
"""

# Make request
response = requests.post(
    "https://api.runpod.io/graphql",
    headers={
        "Content-Type": "application/json",
    },
    params={"api_key": key},
    json={"query": query}
)

# Parse and display results
data = response.json()
if "data" in data and "myself" in data["data"]:
    pub_key = data["data"]["myself"].get("pubKey")

    if not pub_key:
        print("No SSH key found in RunPod account.")
    else:
        print("SSH Public Key registered in RunPod account:\n")
        print(pub_key)
        print("\n" + "=" * 70)

        # Check if it matches runpodctl key
        runpod_key_path = Path.home() / ".runpod" / "ssh" / "RunPod-Key-Go.pub"
        if runpod_key_path.exists():
            runpod_key = runpod_key_path.read_text().strip()
            if pub_key.strip() in runpod_key or runpod_key in pub_key.strip():
                print("✓ This matches the runpodctl key (RunPod-Key-Go)")
            else:
                print("✗ This does NOT match the runpodctl key (RunPod-Key-Go)")
                print("\nThis is the issue! The pod is using a different SSH key.")
else:
    print("Error fetching SSH keys:")
    print(json.dumps(data, indent=2))
