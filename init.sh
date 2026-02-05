#!/bin/bash
# pre_start.sh hook for RunPod pods.
# Sets up non-root user 'rrenaud' with SSH, sudo, and Claude Code.
# Symlinked to /pre_start.sh via dockerArgs so it runs before /start.sh.
set -e

USERNAME="rrenaud"
USER_UID=1000
USER_GID=1000

# Create user with fixed UID (idempotent)
groupadd -g $USER_GID $USERNAME 2>/dev/null || true
useradd -m -u $USER_UID -g $USER_GID -s /bin/bash $USERNAME 2>/dev/null || true

# Passwordless sudo
apt-get update -qq && apt-get install -y -qq sudo > /dev/null 2>&1 || true
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

# Install Claude Code for the user
su - $USERNAME -c 'curl -fsSL https://claude.ai/install.sh | sh' || true

# Persistent Claude config: symlink ~/.claude -> /workspace/.claude_home
CLAUDE_PERSIST="/workspace/.claude_home"
mkdir -p "$CLAUDE_PERSIST"
chown $USERNAME:$USERNAME "$CLAUDE_PERSIST"
ln -sfn "$CLAUDE_PERSIST" "$USER_HOME/.claude"
chown -h $USERNAME:$USERNAME "$USER_HOME/.claude"

# Source RunPod env + add claude to PATH in user's bashrc
cat >> "$USER_HOME/.bashrc" <<'BASHRC'
[ -f /etc/rp_environment ] && source /etc/rp_environment
export PATH="$HOME/.local/bin:$PATH"
BASHRC
chown $USERNAME:$USERNAME "$USER_HOME/.bashrc"

# Own /workspace as the non-root user
chown -R $USERNAME:$USERNAME /workspace
