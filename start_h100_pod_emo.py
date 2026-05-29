#!/usr/bin/env python3
"""Launch an H100 80GB pod on RunPod for the EMO project."""

from pod_manager import PodManager


class H100EmoPodManager(PodManager):
    gpu_type_id = "NVIDIA H100 80GB HBM3"
    pod_name_prefix = "h100-emo"
    network_volume_id = "cfg8twslls"  # 200 GB "emo" volume in US-MO-1
    datacenter_id = "US-MO-1"
    min_memory_gb = 100
    container_disk_gb = 10  # ephemeral root fs only; data lives on the network volume
    vscode_start_dir = "/workspace/EMO"


if __name__ == "__main__":
    H100EmoPodManager().run()
