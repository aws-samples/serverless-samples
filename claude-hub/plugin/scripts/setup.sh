#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# setup.sh - Manual setup for claude-hub (no MDM)
#
# Run after cloning the repo:
#   git clone --depth=1 <repo-url> ~/.claude/claude-hub/repo
#   bash ~/.claude/claude-hub/repo/plugin/scripts/setup.sh --team <team-name>
#
# What it does:
#   1. Writes repo_url (derived from git remote) and team to ~/.claude/claude-hub/
#   2. Adds the SessionStart hook to ~/.claude/settings.json
#   3. Runs the initial sync to populate CLAUDE.md and skills
#
# Safe to run multiple times (idempotent).

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
TEAM=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --team|-t) TEAM="${2:-}"; shift 2 ;;
        --help|-h)
            echo "Usage: bash setup.sh --team <team-name>"
            echo ""
            echo "Options:"
            echo "  --team, -t    Team name (ask your team lead which to use)"
            exit 0
            ;;
        *) echo "Unknown option: $1 (try --help)"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
HUB_DIR="$CLAUDE_DIR/claude-hub"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
SYNC_SCRIPT="$REPO_DIR/plugin/scripts/sync.sh"

# The hook command uses ~ so it works if settings.json is inspected or copied.
# Compute the repo path relative to $HOME.
REPO_REL="${REPO_DIR#$HOME/}"
if [ "$REPO_REL" = "$REPO_DIR" ]; then
    # Repo is not under $HOME, use absolute path
    HOOK_COMMAND="bash $REPO_DIR/plugin/scripts/sync.sh"
else
    HOOK_COMMAND="bash ~/$REPO_REL/plugin/scripts/sync.sh"
fi

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "Error: sync.sh not found at $SYNC_SCRIPT"
    echo "Make sure you cloned the repo to ~/.claude/claude-hub/repo"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required to patch settings.json"
    echo "Install python3 and re-run, or configure the hook manually."
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Write config files
# ---------------------------------------------------------------------------
mkdir -p "$HUB_DIR"

# Derive repo URL from git remote (no need for a separate repo_url file to be set manually)
REPO_URL=$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)
if [ -z "$REPO_URL" ]; then
    echo "Error: could not read remote URL from $REPO_DIR"
    exit 1
fi
echo "$REPO_URL" > "$HUB_DIR/repo_url"
echo "Wrote repo URL: $REPO_URL"

if [ -n "$TEAM" ]; then
    echo "$TEAM" > "$HUB_DIR/team"
    echo "Wrote team: $TEAM"
else
    echo "No --team specified. Org content will sync, but no team content."
    echo "Set a team later: echo \"your-team\" > ~/.claude/claude-hub/team"
fi

# ---------------------------------------------------------------------------
# 2. Install SessionStart hook
# ---------------------------------------------------------------------------
python3 - "$SETTINGS_FILE" "$HOOK_COMMAND" <<'PYEOF'
import json, sys, os

settings_path = sys.argv[1]
hook_command = sys.argv[2]

hook_entry = {
    "matcher": "*",
    "hooks": [
        {
            "type": "command",
            "command": hook_command,
            "timeout": 15
        }
    ]
}

# Read existing settings or start fresh
settings = {}
if os.path.isfile(settings_path):
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        settings = {}

hooks = settings.setdefault("hooks", {})
session_start = hooks.get("SessionStart", [])

# Check if a sync.sh hook is already present
already_installed = False
for entry in session_start:
    for h in entry.get("hooks", []):
        if "sync.sh" in h.get("command", ""):
            already_installed = True
            break

if already_installed:
    print(f"SessionStart hook already present in {settings_path}")
else:
    session_start.append(hook_entry)
    hooks["SessionStart"] = session_start
    settings["hooks"] = hooks

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    print(f"Added SessionStart hook to {settings_path}")
PYEOF

if [ $? -ne 0 ]; then
    echo "Error: failed to configure SessionStart hook"
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Run initial sync
# ---------------------------------------------------------------------------
echo "Running initial sync..."
bash "$SYNC_SCRIPT"

echo ""
echo "Done. Start a new Claude Code session -- sync runs automatically from now on."
