#!/usr/bin/env python3
"""Launch a 3x RTX 3090 pod on RunPod (gd09rqitib volume)."""

from pod_manager import PodManager


class RTX3090x3PodManager(PodManager):
    gpu_type_id = "NVIDIA GeForce RTX 3090"
    gpu_count = 3
    pod_name_prefix = "3090x3-pod"
    network_volume_id = "gd09rqitib"


if __name__ == "__main__":
    RTX3090x3PodManager().run()
