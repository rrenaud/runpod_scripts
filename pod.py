#!/usr/bin/env python3
"""Unified RunPod CLI: list, create, and resume pods.

  pod.py list
  pod.py create <gpu> [--kill-existing] [--dry-run] [--no-vscode]
  pod.py resume [target] [--gpu-count N] [--no-vscode] [--dry-run]

A suspended pod (desiredStatus EXITED, no runtime) keeps its network volume,
GPU, and name, so resuming only needs its id + original gpuCount. `target` is a
pod id or a substring of its name; it may be omitted when exactly one pod is
suspended.
"""

import argparse
import sys

from pod_manager import PodManager
from start_3090_pod import RTX3090PodManager
from start_3090x3_pod import RTX3090x3PodManager
from start_a100_pod import A100PodManager
from start_a100_pod_emo import A100EmoPodManager
from start_rtx_pro_6000_pod import RTXPRO6000PodManager

REGISTRY = {
    "a100-emo": A100EmoPodManager,
    "a100-pcie": A100PodManager,
    "3090": RTX3090PodManager,
    "3090x3": RTX3090x3PodManager,
    "rtx-pro-6000": RTXPRO6000PodManager,
}


def _fmt_pod(p) -> str:
    gpu = (p.get("machine") or {}).get("gpuDisplayName") or "?"
    cost = p.get("costPerHr")
    cost_str = f"${cost:.3f}/hr" if cost is not None else "?"
    suspended = p["desiredStatus"] == "EXITED" and not p["runtime"]
    status = "SUSPENDED" if suspended else p["desiredStatus"]
    return f"  [{status:<10}] {p['name']}  ({p['id']})  {p['gpuCount']}x {gpu}  {cost_str}"


def cmd_list(args) -> int:
    pods = PodManager().get_all_pods()
    if not pods:
        print("No pods found.")
        return 0
    print(f"Pods ({len(pods)}):")
    for p in pods:
        print(_fmt_pod(p))
    return 0


def cmd_create(args) -> int:
    mgr = REGISTRY[args.gpu]()
    mgr.launch_vscode_enabled = not args.no_vscode
    if args.dry_run:
        print(f"[DRY RUN] Would create '{args.gpu}' pod with:")
        mgr.print_config()
        return 0
    mgr.create_and_connect(kill_existing=args.kill_existing)
    return 0


def _resolve_target(pods, target):
    """Pick one pod from `pods` given an id/name `target` (or None)."""
    if target is None:
        if len(pods) == 1:
            return pods[0]
        if not pods:
            print("No suspended pods to resume.")
            return None
        print("Multiple suspended pods — specify an id or name:")
        for p in pods:
            print(_fmt_pod(p))
        return None

    matches = [p for p in pods if p["id"] == target or target in p["name"]]
    if not matches:
        print(f"No suspended pod matching '{target}'.")
        if pods:
            print("Suspended pods:")
            for p in pods:
                print(_fmt_pod(p))
        return None
    if len(matches) > 1:
        print(f"'{target}' matches multiple pods — be more specific:")
        for p in matches:
            print(_fmt_pod(p))
        return None
    return matches[0]


def cmd_resume(args) -> int:
    mgr = PodManager()
    all_pods = mgr.get_all_pods()
    suspended = [p for p in all_pods if p["desiredStatus"] == "EXITED" and not p["runtime"]]

    chosen = _resolve_target(suspended, args.target)
    if chosen is None:
        # If the target names a pod that's already running, just reconnect.
        if args.target:
            running = [
                p for p in all_pods
                if (p["id"] == args.target or args.target in p["name"]) and p["runtime"]
            ]
            if len(running) == 1:
                p = running[0]
                print(f"Pod {p['name']} is already running — reconnecting.")
                mgr.pod_name = p["name"]
                mgr.launch_vscode_enabled = not args.no_vscode
                mgr._connect_after_start(p["id"])
                return 0
        return 2

    gpu_count = args.gpu_count or chosen["gpuCount"]
    mgr.pod_name = chosen["name"]
    mgr.launch_vscode_enabled = not args.no_vscode

    if args.dry_run:
        print(f"[DRY RUN] Would resume {chosen['name']} ({chosen['id']}) "
              f"with {gpu_count} GPU(s).")
        return 0

    mgr.resume_and_connect(chosen["id"], gpu_count)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage RunPod GPU pods.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all pods and their status")

    p_create = sub.add_parser("create", help="Create a new pod")
    p_create.add_argument("gpu", choices=sorted(REGISTRY), help="GPU config to launch")
    p_create.add_argument("--kill-existing", action="store_true",
                          help="Terminate existing pods with the same name prefix first")
    p_create.add_argument("--dry-run", action="store_true",
                          help="Print config and exit without creating")
    p_create.add_argument("--no-vscode", action="store_true",
                          help="Skip launching VSCode after the pod is ready")

    p_resume = sub.add_parser("resume", help="Resume a suspended pod")
    p_resume.add_argument("target", nargs="?",
                          help="Pod id or name substring (optional if exactly one is suspended)")
    p_resume.add_argument("--gpu-count", type=int,
                          help="Override GPU count (defaults to the pod's original count)")
    p_resume.add_argument("--dry-run", action="store_true",
                          help="Show what would be resumed without resuming")
    p_resume.add_argument("--no-vscode", action="store_true",
                          help="Skip launching VSCode after the pod is ready")

    args = parser.parse_args()
    return {"list": cmd_list, "create": cmd_create, "resume": cmd_resume}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
