#!/usr/bin/env python3
"""Launch an A100 80GB PCIe pod on RunPod (CA-MTL-3, superbpe volume)."""

from pod_manager import PodManager


class A100PodManager(PodManager):
    gpu_type_id = "NVIDIA A100 80GB PCIe"
    pod_name_prefix = "a100-pcie-pod"
    network_volume_id = "v8du7ep4yk"  # superbpe 500GB
    datacenter_id = "CA-MTL-3"
    min_vcpu = 8
    min_memory_gb = 100
    vscode_start_dir = "/workspace/assignment5-alignment"


if __name__ == "__main__":
    A100PodManager().run()
