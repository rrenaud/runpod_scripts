#!/bin/bash
# pre_start.sh hook for RunPod pods.
# Sets up non-root user 'rrenaud' with SSH, sudo, and Claude Code.
# Run explicitly via bash in dockerArgs before /start.sh.

USERNAME="rrenaud"
USER_UID=1000
USER_GID=1000

# Create user with fixed UID (idempotent)
groupadd -g $USER_GID $USERNAME 2>/dev/null || true
useradd -m -u $USER_UID -g $USER_GID -s /bin/bash $USERNAME 2>/dev/null || true

# Passwordless sudo
apt-get update -qq && apt-get install -y -qq sudo tmux nano bat less > /dev/null 2>&1 || true
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
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1
apt-get install -y -qq nodejs > /dev/null 2>&1 || true

# Install Claude Code for the user
su - $USERNAME -c 'curl -fsSL https://claude.ai/install.sh | bash' || true

# Persistent Claude config: symlink ~/.claude -> /workspace/.claude_home
CLAUDE_PERSIST="/workspace/.claude_home"
mkdir -p "$CLAUDE_PERSIST"
chown $USERNAME:$USERNAME "$CLAUDE_PERSIST" || true
ln -sfn "$CLAUDE_PERSIST" "$USER_HOME/.claude"
chown -h $USERNAME:$USERNAME "$USER_HOME/.claude"

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
  },
  "terminal.integrated.defaultProfile.linux": "tmux-claude"
}
VSCODE
chown -R $USERNAME:$USERNAME /workspace/.vscode || true

# Launch Claude Code in a tmux session
su - $USERNAME -c 'tmux new-session -d -s claude -c /workspace "claude --dangerously-skip-permissions"' || true
