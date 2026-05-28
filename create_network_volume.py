#!/usr/bin/env python3
"""Create a RunPod network volume.

Usage: create_network_volume.py NAME SIZE_GB DATACENTER_ID
Example: create_network_volume.py emo 200 US-MO-1
"""

import json
import sys
from pathlib import Path

import requests


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    name, size_gb, dc = sys.argv[1], int(sys.argv[2]), sys.argv[3]

    key = (Path.home() / ".runpod_api_key.txt").read_text().strip()
    endpoint = "https://api.runpod.io/graphql"
    headers = {"Content-Type": "application/json"}
    params = {"api_key": key}

    # Runpod's pod-create mutation in pod_manager.py is `podFindAndDeployOnDemand` —
    # subject-first naming. Try the analogous `networkVolumeCreate` first; if the
    # schema rejects it, fall back to `createNetworkVolume`.
    attempts = [
        (
            "networkVolumeCreate",
            """
            mutation CreateNV($input: NetworkVolumeCreateInput!) {
              networkVolumeCreate(input: $input) {
                id name size dataCenterId
              }
            }
            """,
        ),
        (
            "createNetworkVolume",
            """
            mutation CreateNV($input: CreateNetworkVolumeInput!) {
              createNetworkVolume(input: $input) {
                id name size dataCenterId
              }
            }
            """,
        ),
    ]

    variables = {"input": {"name": name, "size": size_gb, "dataCenterId": dc}}

    last_resp = None
    for op_name, mutation in attempts:
        resp = requests.post(
            endpoint,
            headers=headers,
            params=params,
            json={"query": mutation, "variables": variables},
        )
        last_resp = resp.json()
        if "errors" not in last_resp:
            payload = last_resp["data"][op_name]
            print(json.dumps(payload, indent=2))
            return 0
        # Only retry on validation errors (i.e. wrong mutation name); fail fast on others.
        codes = {e.get("extensions", {}).get("code") for e in last_resp.get("errors", [])}
        if "GRAPHQL_VALIDATION_FAILED" not in codes:
            break

    print("Volume creation failed. Last response:", file=sys.stderr)
    print(json.dumps(last_resp, indent=2), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
