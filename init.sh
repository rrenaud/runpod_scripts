#!/bin/bash
# pre_start.sh hook for RunPod pods.
# Sets up non-root user 'rrenaud' with SSH, sudo, and Claude Code.
# Run explicitly via bash in dockerArgs before /start.sh.

USERNAME="rrenaud"

# Create user (idempotent). Try UID 1000, fall back to system-assigned if taken.
if ! id "$USERNAME" &>/dev/null; then
    groupadd -g 1000 $USERNAME 2>/dev/null || groupadd $USERNAME 2>/dev/null || true
    useradd -m -u 1000 -g $USERNAME -s /bin/bash $USERNAME 2>/dev/null \
        || useradd -m -g $USERNAME -s /bin/bash $USERNAME 2>/dev/null || true
fi

# Passwordless sudo
if ! command -v tmux &>/dev/null || ! command -v batcat &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq sudo tmux nano bat less > /dev/null 2>&1 || true
fi
echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME

# SSH access for non-root user (reuses RunPod's PUBLIC_KEY env var)
USER_HOME="/home/$USERNAME"
mkdir -p "$USER_HOME/.ssh"
if [ -n "$PUBLIC_KEY" ]; then
    echo "$PUBLIC_KEY" > "$USER_HOME/.ssh/authorized_keys"
    chmod 700 "$USER_HOME/.ssh"
    chmod 600 "$USER_HOME/.ssh/authorized_keys"
    chown -R $USERNAME:$USERNAME "$USER_HOME/.ssh"
fi

# Install Node.js (required by Claude Code)
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1 || true
fi

# Install Claude Code for the user (skip if already installed)
if ! su - $USERNAME -c 'command -v claude' &>/dev/null; then
    su - $USERNAME -c 'curl -fsSL https://claude.ai/install.sh | bash' || true
fi

# Persistent Claude config: symlink ~/.claude -> /workspace/.claude_home
CLAUDE_PERSIST="/workspace/.claude_home"
mkdir -p "$CLAUDE_PERSIST"
chown $USERNAME:$USERNAME "$CLAUDE_PERSIST" || true
ln -sfn "$CLAUDE_PERSIST" "$USER_HOME/.claude"
chown -h $USERNAME:$USERNAME "$USER_HOME/.claude"

# Persistent .netrc (wandb API key etc): symlink ~/.netrc -> /workspace/.netrc
if [ -f /workspace/.netrc ]; then
    ln -sfn /workspace/.netrc "$USER_HOME/.netrc"
    chown -h $USERNAME:$USERNAME "$USER_HOME/.netrc"
fi

# Git identity and credentials
su - $USERNAME -c 'git config --global user.email "rrenaud@gmail.com"'
su - $USERNAME -c 'git config --global user.name "Rob Neuhaus"'
su - $USERNAME -c 'git config --global credential.helper "store --file /workspace/.git-credentials"'

# Copy persistent config files into ~/.claude
cp /workspace/init/keybindings.json "$USER_HOME/.claude/keybindings.json" 2>/dev/null || true
chown $USERNAME:$USERNAME "$USER_HOME/.claude/keybindings.json" 2>/dev/null || true

# Source RunPod env + add claude to PATH in user's bashrc
cat >> "$USER_HOME/.bashrc" <<'BASHRC'
[ -f /etc/rp_environment ] && source /etc/rp_environment
export PATH="$HOME/.local/bin:$PATH"
export LESS='-R -i -M -F -X'
export PAGER="less"
if command -v batcat &> /dev/null; then
    alias bat='batcat'
fi
# Auto-attach to claude tmux session if no one else is attached
if [ -z "$TMUX" ] && tmux has-session -t claude 2>/dev/null && [ "$(tmux list-clients -t claude 2>/dev/null | wc -l)" -eq 0 ]; then
    exec tmux attach -t claude
fi
BASHRC
chown $USERNAME:$USERNAME "$USER_HOME/.bashrc"

# Own /workspace as the non-root user
chown -R $USERNAME:$USERNAME /workspace || true

# VSCode Remote settings: default terminal attaches to tmux claude session
mkdir -p /workspace/.vscode
cat > /workspace/.vscode/settings.json <<'VSCODE'
{
  "terminal.integrated.profiles.linux": {
    "tmux-claude": {
      "path": "tmux",
      "args": ["attach", "-t", "claude"]
    }
  }
}
VSCODE
chown -R $USERNAME:$USERNAME /workspace/.vscode || true

# Launch Claude Code in a tmux session
su - $USERNAME -c 'tmux new-session -d -s claude -c /workspace "claude --dangerously-skip-permissions"' || true
