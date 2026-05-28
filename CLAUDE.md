# RunPod Scripts - Memory

## Key Learnings

### RunPod sh/bash incompatibility
- RunPod's `/start.sh` sources `/pre_start.sh` with `sh` (dash), ignoring shebangs
- Symlinking a bash script to `/pre_start.sh` causes crash loops with: `Syntax error: "(" unexpected`
- **Fix**: Use `docker_args = "bash -c 'bash /workspace/init/init.sh; exec /start.sh'"` to run init explicitly with bash
- Use `;` not `&&` so `/start.sh` runs even if init.sh fails
- Use `exec` to replace shell (no extra process)
- **Also applies to `curl | sh`**: Claude's install script uses bash syntax, so `curl ... | sh` fails on dash. Always use `curl ... | bash`

### Network volumes and chown
- `chown` on network volumes may fail silently — always add `|| true`
- Don't use `set -e` in init scripts that run on network volumes

### RunPod container environment
- RunPod torch templates do NOT include Node.js
- Claude Code requires Node.js — must install it in init.sh before Claude Code
- Node install: `curl -fsSL https://deb.nodesource.com/setup_22.x | bash -` then `apt-get install nodejs`

### Ubuntu 24.04 UID 1000 conflict
- Newer templates (e.g. `runpod-torch-v280`) use Ubuntu 24.04, which has a default `ubuntu` user at UID/GID 1000
- Hardcoding `useradd -u 1000` fails silently with `|| true`, leaving no user created
- **Fix**: Try UID 1000 first, fall back to system-assigned: `useradd -u 1000 ... || useradd ...`

### Adding new GPU support
- **Always check the template/docker image** — newer GPUs (e.g. Blackwell) need newer CUDA
- Blackwell (sm_120) needs CUDA 12.8+ → use `runpod-torch-v280` (not v240)
- Query available templates: `myself { podTemplates { id name imageName } }`
- Different templates may use different base OS (Ubuntu 22.04 vs 24.04), causing subtle breakage

### SSH readiness timing
- SSH takes ~35s to become ready after pod shows "running" in API
- Poll SSH instead of fixed sleep — 5s intervals, up to 30 attempts works well
- Launch VSCode only after SSH is confirmed ready

## Repo Structure
- `pod.py` — unified CLI; preferred entry point. Subcommands:
  - `pod.py list` — all pods with status (SUSPENDED/RUNNING), gpu, $/hr
  - `pod.py create <gpu>` — create a pod (`<gpu>`: a100-emo, a100-pcie, 3090, 3090x3, rtx-pro-6000). Flags: `--kill-existing`, `--dry-run`, `--no-vscode`
  - `pod.py resume [target]` — resume a suspended pod (id or name substring; optional when exactly one is suspended). Flags: `--gpu-count`, `--dry-run`, `--no-vscode`
- `pod_manager.py` — shared PodManager base class. Create flow: `create_and_connect`; resume flow: `resume_and_connect` → `resume_pod` (uses RunPod `podResume` mutation, dual-name fallback). `_connect_after_start` is shared by both. `get_all_pods`/`get_suspended_pods` for listing. Suspended pod = `desiredStatus == "EXITED"` and `runtime == null`.
- `start_*.py` — per-GPU config subclasses (gpu type, network volume, datacenter, template). Still runnable standalone; `pod.py` imports their classes into its registry.
  - `start_3090_pod.py` (template v240, CUDA 12.4), `start_rtx_pro_6000_pod.py` (RTX PRO 6000 Blackwell, template v280, CUDA 12.8), `start_a100_pod.py`, `start_a100_pod_emo.py`, `start_3090x3_pod.py`
- `init.sh` — pod initialization script (user setup, Node.js, Claude Code, tmux, SSH)
