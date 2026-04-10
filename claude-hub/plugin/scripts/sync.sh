#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# sync.sh - Claude Hub configuration sync script
# Invoked by the SessionStart hook to synchronize org/team CLAUDE.md
# and skills from a central git repository.
#
# Design constraints:
#   - Always exits 0 (never blocks a session)
#   - All output goes to sync.log
#   - File lock prevents concurrent syncs
#   - Graceful offline: uses cached files when fetch fails

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
CLAUDE_DIR="$HOME/.claude"
HUB_DIR="$CLAUDE_DIR/claude-hub"
REPO_DIR="$HUB_DIR/repo"
LOCK_FILE="$HUB_DIR/.lock"
LOG_FILE="$HUB_DIR/sync.log"
LAST_SYNC_FILE="$HUB_DIR/last_sync"
TEAM_FILE="$HUB_DIR/team"
REPO_URL_FILE="$HUB_DIR/repo_url"
TTL_SECONDS=300  # 5 minutes

SKILLS_DIR="$CLAUDE_DIR/skills"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
DRIFT_DIR="$HUB_DIR/drift"

# Claude Code managed policy paths (org CLAUDE.md deployed by MDM)
case "$(uname -s)" in
    Darwin)  MANAGED_POLICY_MD="/Library/Application Support/ClaudeCode/CLAUDE.md" ;;
    CYGWIN*|MINGW*|MSYS*) MANAGED_POLICY_MD="C:/Program Files/ClaudeCode/CLAUDE.md" ;;
    *)       MANAGED_POLICY_MD="/etc/claude-code/CLAUDE.md" ;;
esac

# ---------------------------------------------------------------------------
# Redirect all output to log (append). Truncate if over 100KB to avoid bloat.
# Save stderr on fd 3 so we can print a user-visible summary at the end.
# ---------------------------------------------------------------------------
if [ -f "$LOG_FILE" ] && [ "$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 102400 ]; then
    tail -c 51200 "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE" 2>/dev/null
fi
exec 3>&2
exec >> "$LOG_FILE" 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# ---------------------------------------------------------------------------
# Trap: ensure we always clean up the lock and exit 0
# ---------------------------------------------------------------------------
cleanup() {
    rm -f "$LOCK_FILE"
    log "Sync finished (exit 0)"
}
trap cleanup EXIT

# Override exit to always return 0
exit_ok() {
    exit 0
}

# ---------------------------------------------------------------------------
# Acquire file lock (non-blocking)
# ---------------------------------------------------------------------------
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        # Check if lock is stale (older than 60 seconds)
        local lock_age
        lock_age=$(( $(date +%s) - $(stat -f%m "$LOCK_FILE" 2>/dev/null || stat -c%Y "$LOCK_FILE" 2>/dev/null || echo 0) ))
        if [ "$lock_age" -lt 60 ]; then
            log "Another sync is running (lock age: ${lock_age}s). Skipping."
            # Remove trap so we don't delete someone else's lock
            trap - EXIT
            exit 0
        fi
        log "Stale lock detected (age: ${lock_age}s). Removing."
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
}

# ---------------------------------------------------------------------------
# Read configuration
# ---------------------------------------------------------------------------
read_config() {
    if [ ! -f "$REPO_URL_FILE" ]; then
        log "No repo_url configured at $REPO_URL_FILE. Nothing to sync."
        exit_ok
    fi
    REPO_URL="$(tr -d '[:space:]' < "$REPO_URL_FILE" 2>/dev/null)"
    if [ -z "$REPO_URL" ]; then
        log "repo_url file is empty. Nothing to sync."
        exit_ok
    fi

    TEAM=""
    if [ -f "$TEAM_FILE" ]; then
        TEAM="$(tr -d '[:space:]' < "$TEAM_FILE" 2>/dev/null)"
    fi
    log "Config: repo=$REPO_URL team=${TEAM:-<none>}"
}

# ---------------------------------------------------------------------------
# TTL check: skip if last sync < 5 min ago and HEAD unchanged
# Fast path designed to complete in <10ms
# ---------------------------------------------------------------------------
check_ttl() {
    if [ ! -f "$LAST_SYNC_FILE" ]; then
        return 0  # No previous sync, proceed
    fi

    local last_sync_time
    last_sync_time=$(head -1 "$LAST_SYNC_FILE" 2>/dev/null)
    local now
    now=$(date +%s)
    local elapsed=$(( now - ${last_sync_time:-0} ))

    if [ "$elapsed" -lt "$TTL_SECONDS" ]; then
        # Within TTL - check if HEAD changed (quick local check only)
        local cached_head
        cached_head=$(sed -n '2p' "$LAST_SYNC_FILE" 2>/dev/null)
        if [ -d "$REPO_DIR/.git" ]; then
            local current_head
            current_head=$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null)
            if [ "$cached_head" = "$current_head" ]; then
                log "TTL check: ${elapsed}s elapsed, HEAD unchanged. Skipping."
                exit_ok
            fi
        fi
    fi
    return 0  # TTL expired or HEAD changed, proceed
}

# ---------------------------------------------------------------------------
# Clone or fetch the repository
# ---------------------------------------------------------------------------
sync_repo() {
    if [ ! -d "$REPO_DIR/.git" ]; then
        # First run: clone
        log "First run - cloning $REPO_URL into $REPO_DIR"
        mkdir -p "$REPO_DIR"
        if ! timeout 30 git clone --depth=1 "$REPO_URL" "$REPO_DIR" 2>&1; then
            log "ERROR: git clone failed. Will retry next session."
            exit_ok
        fi
        CLONE_FRESH=1
    else
        # Subsequent runs: fetch with 3s timeout
        log "Fetching updates..."
        local old_head
        old_head=$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null)

        if ! timeout 3 git -C "$REPO_DIR" fetch --depth=1 origin 2>&1; then
            log "WARN: git fetch failed (offline?). Using cached files."
            FETCH_FAILED=1
            return 0
        fi

        # Check if there are changes
        local remote_head
        remote_head=$(git -C "$REPO_DIR" rev-parse FETCH_HEAD 2>/dev/null)
        if [ "$old_head" = "$remote_head" ] && [ -f "$CLAUDE_MD" ]; then
            log "No changes detected (HEAD: ${old_head:0:7}). Skipping rebuild."
            # Update sync timestamp even though no changes
            update_last_sync
            exit_ok
        fi

        # Fast-forward to fetched HEAD
        git -C "$REPO_DIR" reset --hard FETCH_HEAD 2>&1 || true
        log "Updated repo: ${old_head:0:7} -> ${remote_head:0:7}"
    fi
}

# ---------------------------------------------------------------------------
# Build ~/.claude/CLAUDE.md
#
# Two modes based on whether org CLAUDE.md is deployed to the managed policy
# path (by MDM) or not:
#
#   MDM mode:     Managed policy has org content. Sync writes team-only.
#   Plugin mode:  No managed policy. Sync writes org + team (combined).
# ---------------------------------------------------------------------------
build_claude_md() {
    local org_md="$REPO_DIR/org/CLAUDE.md"
    local team_md=""
    if [ -n "$TEAM" ]; then
        team_md="$REPO_DIR/teams/$TEAM/CLAUDE.md"
    fi

    # Detect deployment mode
    local mdm_mode=0
    if [ -f "$MANAGED_POLICY_MD" ]; then
        mdm_mode=1
        log "Managed policy CLAUDE.md found at $MANAGED_POLICY_MD — team-only mode"
    else
        log "No managed policy CLAUDE.md — writing org + team"
    fi

    # Compute short SHAs for provenance
    local repo_sha
    repo_sha=$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    local team_sha=""
    if [ -n "$TEAM" ] && [ -f "$team_md" ]; then
        team_sha=$(git -C "$REPO_DIR" log -1 --format=%h -- "teams/$TEAM/CLAUDE.md" 2>/dev/null || echo "$repo_sha")
    fi

    # Build provenance header
    local date_str
    date_str=$(date '+%Y-%m-%d %H:%M:%S')
    local provenance="<!-- Generated by claude-hub"
    if [ "$mdm_mode" -eq 0 ]; then
        provenance="${provenance} | org:${repo_sha}"
    fi
    if [ -n "$TEAM" ]; then
        provenance="${provenance} | team:${TEAM}:${team_sha:-$repo_sha}"
    fi
    provenance="${provenance} | ${date_str} -->"

    # Concatenate content
    local content="$provenance"
    content="${content}
"

    # Include org content only in plugin-only mode (no MDM)
    if [ "$mdm_mode" -eq 0 ]; then
        if [ -f "$org_md" ]; then
            content="${content}
$(cat "$org_md")"
            log "Included org CLAUDE.md"
        else
            log "WARN: No org CLAUDE.md found at $org_md"
        fi
    fi

    # Always include team content
    if [ -n "$TEAM" ] && [ -f "$team_md" ]; then
        content="${content}

<!-- Team: ${TEAM} (${team_sha:-$repo_sha}) -->
$(cat "$team_md")"
        log "Included team CLAUDE.md for '$TEAM'"
    elif [ -n "$TEAM" ]; then
        log "WARN: No team CLAUDE.md found at $team_md"
    fi

    # Write atomically (write to temp, then move)
    local tmp_md
    tmp_md=$(mktemp "$CLAUDE_DIR/.CLAUDE.md.XXXXXX")
    printf '%s\n' "$content" > "$tmp_md"
    mv "$tmp_md" "$CLAUDE_MD"
    log "Wrote $CLAUDE_MD"
}

# ---------------------------------------------------------------------------
# Copy skills from org and team directories, prefixed with hub-
# ---------------------------------------------------------------------------
sync_skills() {
    mkdir -p "$SKILLS_DIR"

    # Remove previously synced hub- skills to avoid stale entries
    # Skills are directories (containing SKILL.md), not flat files
    find "$SKILLS_DIR" -maxdepth 1 -name 'hub-*' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$SKILLS_DIR" -maxdepth 1 -name 'hub-*' -type f -delete 2>/dev/null || true
    log "Cleared old hub-* skills"

    ORG_SKILL_COUNT=0
    TEAM_SKILL_COUNT=0

    # Copy org skills (skills are directories containing SKILL.md)
    local org_skills_dir="$REPO_DIR/org/skills"
    if [ -d "$org_skills_dir" ]; then
        for skill_entry in "$org_skills_dir"/*; do
            [ -d "$skill_entry" ] || continue
            local basename
            basename=$(basename "$skill_entry")
            cp -r "$skill_entry" "$SKILLS_DIR/hub-${basename}"
            ORG_SKILL_COUNT=$((ORG_SKILL_COUNT + 1))
        done
        log "Copied $ORG_SKILL_COUNT org skill(s)"
    fi

    # Copy team skills (may override org skills with same name)
    if [ -n "$TEAM" ]; then
        local team_skills_dir="$REPO_DIR/teams/$TEAM/skills"
        if [ -d "$team_skills_dir" ]; then
            for skill_entry in "$team_skills_dir"/*; do
                [ -d "$skill_entry" ] || continue
                local basename
                basename=$(basename "$skill_entry")
                cp -r "$skill_entry" "$SKILLS_DIR/hub-${basename}"
                TEAM_SKILL_COUNT=$((TEAM_SKILL_COUNT + 1))
            done
            log "Copied $TEAM_SKILL_COUNT team skill(s) for '$TEAM'"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Merge settings from org and team settings.json into user settings
#
# Reads mcpServers, extraKnownMarketplaces, and enabledPlugins from
# org/settings.json and teams/<team>/settings.json, merges them (team
# overrides org for same key), and writes the result into
# ~/.claude/settings.json without touching other keys.
#
# Tracks which entries were added by hub in separate files so stale
# entries can be cleaned up when removed from the repo.
# ---------------------------------------------------------------------------
MANAGED_MCP_FILE="$HUB_DIR/managed_mcp_servers"
MANAGED_MARKETPLACES_FILE="$HUB_DIR/managed_marketplaces"
MANAGED_PLUGINS_FILE="$HUB_DIR/managed_plugins"
USER_SETTINGS="$CLAUDE_DIR/settings.json"

sync_mcp_servers() {
    # Skip if python3 is not available (needed for JSON merging)
    if ! command -v python3 >/dev/null 2>&1; then
        log "WARN: python3 not found, skipping MCP server sync"
        return 0
    fi

    # In MDM mode, org MCP servers are in the managed policy settings.json.
    # Only sync team MCP servers to user settings.
    local mdm_mode=0
    if [ -f "$MANAGED_POLICY_MD" ]; then
        mdm_mode=1
    fi

    local org_settings="$REPO_DIR/org/settings.json"
    local team_settings=""
    if [ -n "$TEAM" ]; then
        team_settings="$REPO_DIR/teams/$TEAM/settings.json"
    fi

    # Check if there are any settings configs to sync
    # In MDM mode, org mcpServers are in managed-settings.json, but
    # enabledPlugins and extraKnownMarketplaces still need user settings.json
    local has_org=0 has_team=0
    if [ -f "$org_settings" ]; then
        has_org=1
    fi
    if [ -n "$team_settings" ] && [ -f "$team_settings" ]; then
        has_team=1
    fi

    if [ "$has_org" -eq 0 ] && [ "$has_team" -eq 0 ]; then
        # No configs to sync, but clean up any previously managed entries
        local cleaned=0
        for managed_file in "$MANAGED_MCP_FILE" "$MANAGED_MARKETPLACES_FILE" "$MANAGED_PLUGINS_FILE"; do
            if [ -f "$managed_file" ]; then
                cleaned=1
            fi
        done
        if [ "$cleaned" -eq 1 ]; then
            _remove_managed_settings_entries
            rm -f "$MANAGED_MCP_FILE" "$MANAGED_MARKETPLACES_FILE" "$MANAGED_PLUGINS_FILE"
            log "Removed previously managed settings entries (none configured now)"
        fi
        return 0
    fi

    # Merge org (if not MDM) and team settings, then write to user settings.
    # Handles mcpServers, extraKnownMarketplaces, and enabledPlugins.
    python3 - "$org_settings" "$team_settings" "$USER_SETTINGS" "$MANAGED_MCP_FILE" "$MANAGED_MARKETPLACES_FILE" "$MANAGED_PLUGINS_FILE" "$mdm_mode" <<'PYEOF'
import json, sys, os

org_path, team_path, settings_path, managed_mcp_path, managed_mktp_path, managed_plug_path, mdm_mode = sys.argv[1:8]
mdm_mode = mdm_mode == "1"

def load_json(path):
    if path and os.path.isfile(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def load_managed(path):
    if os.path.isfile(path):
        with open(path) as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_managed(path, names):
    with open(path, "w") as f:
        for name in sorted(names):
            f.write(name + "\n")

def merge_dict_key(settings, key, hub_entries, prev_managed):
    """Merge a dict-valued key: remove stale hub entries, add/update current ones."""
    current = settings.get(key, {})
    for name in prev_managed:
        if name not in hub_entries and name in current:
            del current[name]
    current.update(hub_entries)
    if current:
        settings[key] = current
    elif key in settings:
        del settings[key]
    return set(hub_entries.keys())

org = load_json(org_path)
team = load_json(team_path)

# Collect hub-managed entries (org + team, team wins on conflict)
# In MDM mode, org mcpServers are in managed-settings.json — skip them here
hub_servers = {}
if not mdm_mode:
    hub_servers.update(org.get("mcpServers", {}))
hub_servers.update(team.get("mcpServers", {}))

hub_marketplaces = {}
hub_marketplaces.update(org.get("extraKnownMarketplaces", {}))
hub_marketplaces.update(team.get("extraKnownMarketplaces", {}))

hub_plugins = {}
hub_plugins.update(org.get("enabledPlugins", {}))
hub_plugins.update(team.get("enabledPlugins", {}))

# Read existing user settings
settings = load_json(settings_path)

# Merge each key with cleanup of stale entries
managed_mcp = merge_dict_key(settings, "mcpServers", hub_servers, load_managed(managed_mcp_path))
managed_mktp = merge_dict_key(settings, "extraKnownMarketplaces", hub_marketplaces, load_managed(managed_mktp_path))
managed_plug = merge_dict_key(settings, "enabledPlugins", hub_plugins, load_managed(managed_plug_path))

# Write updated settings
with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")

# Write current managed names for next sync
save_managed(managed_mcp_path, managed_mcp)
save_managed(managed_mktp_path, managed_mktp)
save_managed(managed_plug_path, managed_plug)
PYEOF

    if [ $? -eq 0 ]; then
        local mcp_count mktp_count plug_count
        mcp_count=$(wc -l < "$MANAGED_MCP_FILE" 2>/dev/null | tr -d ' ')
        mktp_count=$(wc -l < "$MANAGED_MARKETPLACES_FILE" 2>/dev/null | tr -d ' ')
        plug_count=$(wc -l < "$MANAGED_PLUGINS_FILE" 2>/dev/null | tr -d ' ')
        log "Synced ${mcp_count:-0} MCP server(s), ${mktp_count:-0} marketplace(s), ${plug_count:-0} plugin(s) to $USER_SETTINGS"
    else
        log "WARN: settings sync failed"
    fi
}

# Remove hub-managed entries from user settings (cleanup helper)
_remove_managed_settings_entries() {
    [ -f "$USER_SETTINGS" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0

    python3 - "$USER_SETTINGS" "$MANAGED_MCP_FILE" "$MANAGED_MARKETPLACES_FILE" "$MANAGED_PLUGINS_FILE" <<'PYEOF'
import json, sys, os
settings_path, mcp_path, mktp_path, plug_path = sys.argv[1:5]
if not os.path.isfile(settings_path):
    sys.exit(0)
try:
    with open(settings_path) as f:
        settings = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(0)

changed = False
for managed_path, key in [(mcp_path, "mcpServers"), (mktp_path, "extraKnownMarketplaces"), (plug_path, "enabledPlugins")]:
    if not os.path.isfile(managed_path):
        continue
    with open(managed_path) as f:
        managed = set(line.strip() for line in f if line.strip())
    section = settings.get(key, {})
    for name in managed:
        if name in section:
            del section[name]
            changed = True
    if section:
        settings[key] = section
    elif key in settings:
        del settings[key]
        changed = True

if changed:
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
PYEOF
}

# ---------------------------------------------------------------------------
# Fragment drift detection
# ---------------------------------------------------------------------------

# Marker delimiters used in CLAUDE.md
FRAGMENT_BEGIN="claude-hub:fragment:begin"
FRAGMENT_END="claude-hub:fragment:end"

# Extract the managed section from a CLAUDE.md (content between markers)
extract_managed_section() {
    local file="$1"
    sed -n "/${FRAGMENT_BEGIN}/,/${FRAGMENT_END}/p" "$file"
}

# Compute SHA-256 hash of fragment-managed content (must match generate-markers.sh)
# Includes: .claude/ files (excluding .fragment) + managed section of CLAUDE.md
compute_fragment_hash() {
    local frag_dir="$1"
    local hash_input=""

    if [ -d "$frag_dir/.claude" ]; then
        hash_input=$(find "$frag_dir/.claude" -type f ! -name '.fragment' | sort | while read -r f; do
            local rel="${f#$frag_dir/}"
            echo "---FILE:${rel}---"
            cat "$f"
        done)
    fi

    # Hash the managed section of CLAUDE.md (between markers only)
    if [ -f "$frag_dir/CLAUDE.md" ]; then
        local managed
        managed=$(extract_managed_section "$frag_dir/CLAUDE.md")
        if [ -n "$managed" ]; then
            hash_input="${hash_input}
---FILE:CLAUDE.md:managed---
${managed}"
        fi
    fi

    if [ -z "$hash_input" ]; then
        echo "empty"
        return
    fi

    printf '%s' "$hash_input" | shasum -a 256 | cut -d' ' -f1
}

# Get a stable hash of a path for use as a filename
path_hash() {
    if command -v md5 >/dev/null 2>&1; then
        md5 -qs "$1"
    else
        printf '%s' "$1" | md5sum | cut -d' ' -f1
    fi
}

# Check if the current project's fragment is outdated
check_fragment_drift() {
    local project_dir="$PWD"
    local marker_file="$project_dir/.claude/.fragment"

    if [ ! -f "$marker_file" ]; then
        log "No .fragment marker in $project_dir — skipping drift check"
        return 0
    fi

    # Parse marker file
    local fragment_name="" marker_hash=""
    while IFS='=' read -r key value; do
        case "$key" in
            fragment) fragment_name="$value" ;;
            hash) marker_hash="$value" ;;
        esac
    done < "$marker_file"

    if [ -z "$fragment_name" ] || [ -z "$marker_hash" ]; then
        log "WARN: Malformed .fragment marker in $project_dir — skipping drift check"
        return 0
    fi

    # Check both locations: examples/fragments/ (default) and fragments/ (custom)
    local source_dir="$REPO_DIR/examples/fragments/$fragment_name"
    if [ ! -d "$source_dir" ]; then
        source_dir="$REPO_DIR/fragments/$fragment_name"
    fi
    if [ ! -d "$source_dir" ]; then
        log "WARN: Fragment '$fragment_name' no longer exists in repo"
        write_drift_notice "$project_dir" "$fragment_name" "missing"
        return 0
    fi

    # Compute current hash of the source fragment
    local current_hash
    current_hash=$(compute_fragment_hash "$source_dir")

    if [ "$marker_hash" = "$current_hash" ]; then
        log "Fragment '$fragment_name' is up to date (hash: ${current_hash:0:12}...)"
        clear_drift_notice "$project_dir"
    else
        log "Fragment '$fragment_name' has updates (project: ${marker_hash:0:12}... -> source: ${current_hash:0:12}...)"
        write_drift_notice "$project_dir" "$fragment_name" "outdated"
    fi
}

# Write a drift notice JSON file
write_drift_notice() {
    local project_path="$1"
    local fragment_name="$2"
    local drift_status="$3"

    mkdir -p "$DRIFT_DIR"
    local phash
    phash=$(path_hash "$project_path")
    local drift_file="$DRIFT_DIR/${phash}.json"
    local detected_at
    detected_at=$(date -u '+%Y-%m-%dT%H:%M:%S')

    cat > "$drift_file" <<EOF
{
  "project_path": "$project_path",
  "fragment": "$fragment_name",
  "status": "$drift_status",
  "detected_at": "$detected_at"
}
EOF
    log "Wrote drift notice: $drift_file"
}

# Remove drift notice when fragment is up to date
clear_drift_notice() {
    local project_path="$1"
    local phash
    phash=$(path_hash "$project_path")
    local drift_file="$DRIFT_DIR/${phash}.json"

    if [ -f "$drift_file" ]; then
        rm -f "$drift_file"
        log "Cleared drift notice: $drift_file"
    fi
}

# Append fragment drift notices to CLAUDE.md
append_drift_notices() {
    if [ ! -d "$DRIFT_DIR" ]; then
        return 0
    fi

    local notices=()
    for drift_file in "$DRIFT_DIR"/*.json; do
        [ -f "$drift_file" ] || continue

        local project_path="" fragment="" drift_status=""
        # Parse JSON with basic shell (no jq dependency)
        while IFS= read -r line; do
            case "$line" in
                *\"project_path\"*) project_path=$(echo "$line" | sed 's/.*: *"//;s/".*//')  ;;
                *\"fragment\"*) fragment=$(echo "$line" | sed 's/.*: *"//;s/".*//')  ;;
                *\"status\"*) drift_status=$(echo "$line" | sed 's/.*: *"//;s/".*//')  ;;
            esac
        done < "$drift_file"

        if [ -n "$project_path" ] && [ -n "$fragment" ]; then
            if [ "$drift_status" = "outdated" ]; then
                notices+=("- Project at \`$project_path\` uses fragment \`$fragment\` which has updates. Use \`/hub-fragment-update\` to review and apply.")
            elif [ "$drift_status" = "missing" ]; then
                notices+=("- Project at \`$project_path\` uses fragment \`$fragment\` which no longer exists in the central repo. Project config is now fully project-owned.")
            fi
        fi
    done

    if [ ${#notices[@]} -eq 0 ]; then
        return 0
    fi

    # Remove any existing fragment notices section from CLAUDE.md
    local tmp_md
    tmp_md=$(mktemp "$CLAUDE_DIR/.CLAUDE.md.drift.XXXXXX")
    sed '/<!-- claude-hub:fragment-notices -->/,/<!-- \/claude-hub:fragment-notices -->/d' "$CLAUDE_MD" > "$tmp_md"

    # Append new notices
    {
        echo ""
        echo "<!-- claude-hub:fragment-notices -->"
        echo "## Fragment Updates Available"
        echo ""
        for notice in "${notices[@]}"; do
            echo "$notice"
        done
        echo "<!-- /claude-hub:fragment-notices -->"
    } >> "$tmp_md"

    mv "$tmp_md" "$CLAUDE_MD"
    log "Appended ${#notices[@]} drift notice(s) to CLAUDE.md"
}

# ---------------------------------------------------------------------------
# Record sync timestamp and HEAD for TTL checks
# ---------------------------------------------------------------------------
update_last_sync() {
    local head
    head=$(git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
    printf '%s\n%s\n' "$(date +%s)" "$head" > "$LAST_SYNC_FILE"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log "=== Sync starting (PID: $$) ==="

    # Ensure hub directory exists
    mkdir -p "$HUB_DIR"

    acquire_lock
    read_config
    check_ttl

    CLONE_FRESH=0
    FETCH_FAILED=0
    sync_repo

    # Build outputs (even if fetch failed, we have cached repo)
    if [ -d "$REPO_DIR/.git" ]; then
        check_fragment_drift || true
        build_claude_md
        append_drift_notices || true
        sync_skills
        sync_mcp_servers || true
        update_last_sync

        # Print user-visible summary to stderr (fd 3) and log
        local summary="claude-hub: synced"
        if [ -n "$TEAM" ]; then
            summary="$summary ($TEAM"
        fi
        summary="$summary, ${ORG_SKILL_COUNT:-0} org + ${TEAM_SKILL_COUNT:-0} team skills)"
        log "$summary"
        echo "$summary" >&3 2>/dev/null || true
    else
        log "ERROR: No repo available. Skipping build."
        echo "claude-hub: sync failed (no repo). See ~/.claude/claude-hub/sync.log" >&3 2>/dev/null || true
    fi

    log "=== Sync complete ==="
}

main
