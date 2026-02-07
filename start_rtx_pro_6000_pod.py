#!/usr/bin/env python3
"""Launch an RTX PRO 6000 Blackwell pod on RunPod (gd09rqitib volume)."""

from pod_manager import PodManager


class RTXPRO6000PodManager(PodManager):
    gpu_type_id = "NVIDIA RTX PRO 6000 Blackwell Server Edition"
    pod_name_prefix = "rtx-pro-6000-pod"
    network_volume_id = "gd09rqitib"
    datacenter_id = ""
    min_vcpu = 8
    min_memory_gb = 30
    vscode_start_dir = "/workspace"


if __name__ == "__main__":
    RTXPRO6000PodManager().run()
