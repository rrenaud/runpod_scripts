#!/usr/bin/env python3
"""Launch an A100 SXM 80GB pod on RunPod for the EMO project."""

from pod_manager import PodManager


class A100EmoPodManager(PodManager):
    gpu_type_id = "NVIDIA A100-SXM4-80GB"
    pod_name_prefix = "a100-emo"
    network_volume_id = "cfg8twslls"  # 200 GB "emo" volume in US-MO-1
    datacenter_id = "US-MO-1"
    min_memory_gb = 100
    vscode_start_dir = "/workspace/EMO"


if __name__ == "__main__":
    A100EmoPodManager().run()
