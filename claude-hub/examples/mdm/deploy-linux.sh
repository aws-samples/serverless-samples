#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# deploy-linux.sh — Ansible/Chef/Puppet compatible deployment for claude-hub
# Installs the claude-hub plugin, deploys org CLAUDE.md to the managed policy
# path, and configures team membership.
#
# Claude Code reads the managed policy CLAUDE.md from:
#   /etc/claude-code/CLAUDE.md
# This file cannot be excluded by individual users and is always loaded.
#
# Environment variables:
#   CLAUDE_HUB_TEAM     — Team name (required, e.g., "platform")
#   CLAUDE_HUB_REPO_URL — Repo URL  (required, e.g., "https://github.com/myorg/claude-hub.git")
#   CLAUDE_HUB_USER     — Target user (optional; defaults to current user or SUDO_USER)

set -euo pipefail

LOG_TAG="claude-hub-deploy"

log() {
    logger -t "$LOG_TAG" "$1" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_error() {
    logger -t "$LOG_TAG" "ERROR: $1" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

die() {
    log_error "$1"
    exit 1
}

# --- Validate parameters ---
TEAM="${CLAUDE_HUB_TEAM:-}"
REPO_URL="${CLAUDE_HUB_REPO_URL:-}"
TARGET_USER="${CLAUDE_HUB_USER:-}"

[ -n "$TEAM" ]     || die "CLAUDE_HUB_TEAM is required"
[ -n "$REPO_URL" ] || die "CLAUDE_HUB_REPO_URL is required"

# --- Resolve target user ---
if [ -z "$TARGET_USER" ]; then
    if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
        TARGET_USER="$SUDO_USER"
    elif [ "$(id -u)" -eq 0 ]; then
        die "Running as root without CLAUDE_HUB_USER or SUDO_USER set. Specify the target user."
    else
        TARGET_USER="$(whoami)"
    fi
fi

# Resolve home directory
USER_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
[ -n "$USER_HOME" ] && [ -d "$USER_HOME" ] || die "Home directory for user $TARGET_USER not found"

log "Deploying claude-hub for user=$TARGET_USER home=$USER_HOME team=$TEAM"

# --- Helper to run commands as target user ---
run_as_user() {
    if [ "$(id -u)" -eq 0 ] && [ "$(whoami)" != "$TARGET_USER" ]; then
        su - "$TARGET_USER" -c "$*"
    else
        eval "$*"
    fi
}

# --- Directory structure ---
CLAUDE_DIR="$USER_HOME/.claude"
HUB_DIR="$CLAUDE_DIR/claude-hub"
PLUGIN_DEST="$CLAUDE_DIR/plugins/local/claude-hub"

mkdir -p "$HUB_DIR"
mkdir -p "$PLUGIN_DEST"

# --- Write config files ---
echo -n "$TEAM" > "$HUB_DIR/team"
echo -n "$REPO_URL" > "$HUB_DIR/repo_url"
log "Wrote team=$TEAM and repo_url to $HUB_DIR"

# --- Check git is available ---
command -v git >/dev/null 2>&1 || die "git is not installed"

# --- Clone or update central repo ---
REPO_CLONE_DIR="$HUB_DIR/repo"
if [ -d "$REPO_CLONE_DIR/.git" ]; then
    log "Repo already cloned, pulling latest..."
    git -C "$REPO_CLONE_DIR" fetch --depth=1 origin 2>&1 | while read -r line; do log "git: $line"; done
    git -C "$REPO_CLONE_DIR" reset --hard origin/HEAD 2>&1 | while read -r line; do log "git: $line"; done
else
    log "Cloning repo $REPO_URL..."
    rm -rf "$REPO_CLONE_DIR"
    git clone --depth=1 "$REPO_URL" "$REPO_CLONE_DIR" 2>&1 | while read -r line; do log "git: $line"; done
fi

# --- Deploy org files to managed policy path ---
MANAGED_POLICY_DIR="/etc/claude-code"
mkdir -p "$MANAGED_POLICY_DIR"

ORG_CLAUDE_MD="$REPO_CLONE_DIR/org/CLAUDE.md"
if [ -f "$ORG_CLAUDE_MD" ]; then
    cp "$ORG_CLAUDE_MD" "$MANAGED_POLICY_DIR/CLAUDE.md"
    chmod 644 "$MANAGED_POLICY_DIR/CLAUDE.md"
    log "Deployed org CLAUDE.md to $MANAGED_POLICY_DIR/CLAUDE.md"
else
    log "Warning: org/CLAUDE.md not found in repo, skipping managed policy CLAUDE.md"
fi

ORG_SETTINGS="$REPO_CLONE_DIR/org/settings.json"
if [ -f "$ORG_SETTINGS" ]; then
    cp "$ORG_SETTINGS" "$MANAGED_POLICY_DIR/managed-settings.json"
    chmod 644 "$MANAGED_POLICY_DIR/managed-settings.json"
    log "Deployed org settings.json to $MANAGED_POLICY_DIR/managed-settings.json (MCP servers, marketplaces, plugins)"
else
    log "Warning: org/settings.json not found in repo, skipping managed policy settings"
fi

# --- Copy plugin files ---
PLUGIN_SRC="$REPO_CLONE_DIR/plugin"
if [ -d "$PLUGIN_SRC" ]; then
    log "Copying plugin files from $PLUGIN_SRC to $PLUGIN_DEST"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete "$PLUGIN_SRC/" "$PLUGIN_DEST/"
    else
        rm -rf "$PLUGIN_DEST"/*
        cp -a "$PLUGIN_SRC"/. "$PLUGIN_DEST/"
    fi
else
    die "Plugin source directory not found at $PLUGIN_SRC"
fi

# --- Add SessionStart hook to settings.json ---
USER_SETTINGS="$CLAUDE_DIR/settings.json"
if command -v python3 >/dev/null 2>&1; then
    python3 - "$USER_SETTINGS" "$PLUGIN_DEST" <<'PYEOF'
import json, sys, os

settings_path, plugin_dest = sys.argv[1:3]
sync_command = f"bash {plugin_dest}/scripts/sync.sh"

if os.path.isfile(settings_path):
    with open(settings_path) as f:
        data = json.load(f)
else:
    data = {}

# Add SessionStart hook if not already present
hooks = data.setdefault("hooks", {})
session_hooks = hooks.get("SessionStart", [])

already_exists = False
for entry in session_hooks:
    for h in entry.get("hooks", []):
        if "sync.sh" in h.get("command", ""):
            already_exists = True
            break

if not already_exists:
    session_hooks.append({
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": sync_command,
            "timeout": 15
        }]
    })
    hooks["SessionStart"] = session_hooks

with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
    log "Added SessionStart hook to $USER_SETTINGS"
else
    log "Warning: python3 not found, could not configure settings.json"
fi

# --- Fix ownership ---
if [ "$(id -u)" -eq 0 ]; then
    chown -R "$TARGET_USER":"$(id -gn "$TARGET_USER")" "$CLAUDE_DIR"
    log "Fixed ownership of $CLAUDE_DIR for $TARGET_USER"
fi

# --- Run initial sync ---
SYNC_SCRIPT="$PLUGIN_DEST/scripts/sync.sh"
if [ -f "$SYNC_SCRIPT" ]; then
    chmod +x "$SYNC_SCRIPT"
    log "Running initial sync..."
    CLAUDE_PLUGIN_ROOT="$PLUGIN_DEST" run_as_user "bash '$SYNC_SCRIPT'" 2>&1 | while read -r line; do log "sync: $line"; done
    log "Initial sync completed"
else
    log "Warning: sync script not found at $SYNC_SCRIPT, skipping initial sync"
fi

log "claude-hub deployment completed successfully"
exit 0
