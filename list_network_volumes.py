#!/usr/bin/env python3
"""List RunPod network volumes to find their IDs."""

import json
import requests
from pathlib import Path

# Read API key
api_key = Path.home() / ".runpod_api_key.txt"
key = api_key.read_text().strip()

# GraphQL query to list network volumes
query = """
query NetworkVolumes {
  myself {
    networkVolumes {
      id
      name
      size
      dataCenterId
    }
  }
}
"""

# Make request
response = requests.post(
    "https://api.runpod.io/graphql",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    },
    json={"query": query}
)

# Parse and display results
data = response.json()
if "data" in data and "myself" in data["data"]:
    volumes = data["data"]["myself"]["networkVolumes"]

    if not volumes:
        print("No network volumes found.")
    else:
        print(f"Found {len(volumes)} network volume(s):\n")
        for vol in volumes:
            print(f"Name: {vol['name']}")
            print(f"ID: {vol['id']}")
            print(f"Size: {vol['size']} GB")
            print(f"Datacenter: {vol['dataCenterId']}")
            print("-" * 50)
else:
    print("Error fetching network volumes:")
    print(json.dumps(data, indent=2))
