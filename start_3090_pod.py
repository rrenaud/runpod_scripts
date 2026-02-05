#!/usr/bin/env python3
"""Launch an RTX 3090 pod on RunPod (EU-CZ-1, gd09rqitib volume)."""

from pod_manager import PodManager


class RTX3090PodManager(PodManager):
    gpu_type_id = "NVIDIA GeForce RTX 3090"
    pod_name_prefix = "3090-pod"
    network_volume_id = "gd09rqitib"
    datacenter_id = "EU-CZ-1"
    min_vcpu = 8
    min_memory_gb = 30
    vscode_start_dir = "/workspace"


if __name__ == "__main__":
    RTX3090PodManager().run()
