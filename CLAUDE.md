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

### SSH readiness timing
- SSH takes ~35s to become ready after pod shows "running" in API
- Poll SSH instead of fixed sleep — 5s intervals, up to 30 attempts works well
- Launch VSCode only after SSH is confirmed ready

## Repo Structure
- `pod_manager.py` — shared PodManager base class
- `start_3090_pod.py` — 3090-specific launcher (subclass)
- `init.sh` — pod initialization script (user setup, Node.js, Claude Code, SSH)
