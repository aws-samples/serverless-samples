#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# generate-markers.sh - Generate .fragment marker files for each fragment directory.
# Run this in CI or manually after updating fragments.
# Each marker contains a content hash so projects can detect drift.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FRAGMENTS_DIR="${1:-$EXAMPLES_DIR/fragments}"

# Marker delimiters used in CLAUDE.md
FRAGMENT_BEGIN="claude-hub:fragment:begin"
FRAGMENT_END="claude-hub:fragment:end"

# ---------------------------------------------------------------------------
# Extract the managed section from a CLAUDE.md (content between markers).
# Returns empty string if markers are not found.
# ---------------------------------------------------------------------------
extract_managed_section() {
    local file="$1"
    sed -n "/${FRAGMENT_BEGIN}/,/${FRAGMENT_END}/p" "$file"
}

# ---------------------------------------------------------------------------
# Compute a SHA-256 hash of fragment-managed content.
# Includes: .claude/ files (excluding .fragment) + managed section of CLAUDE.md
# ---------------------------------------------------------------------------
compute_fragment_hash() {
    local frag_dir="$1"
    local hash_input=""

    # Hash files under .claude/ (fragment-managed)
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

# ---------------------------------------------------------------------------
# Get comma-separated list of tracked (fragment-managed) files.
# ---------------------------------------------------------------------------
get_tracked_files() {
    local frag_dir="$1"
    local files=()

    if [ -d "$frag_dir/.claude" ]; then
        while IFS= read -r f; do
            files+=("${f#$frag_dir/}")
        done < <(find "$frag_dir/.claude" -type f ! -name '.fragment' | sort)
    fi

    # Include CLAUDE.md only if it has the managed section markers
    if [ -f "$frag_dir/CLAUDE.md" ]; then
        local managed
        managed=$(extract_managed_section "$frag_dir/CLAUDE.md")
        if [ -n "$managed" ]; then
            files+=("CLAUDE.md")
        fi
    fi

    if [ ${#files[@]} -eq 0 ]; then
        echo ""
        return
    fi
    local IFS=','
    echo "${files[*]}"
}

# ---------------------------------------------------------------------------
# Main: iterate over fragments and generate markers
# ---------------------------------------------------------------------------
main() {
    if [ ! -d "$FRAGMENTS_DIR" ]; then
        echo "ERROR: fragments/ directory not found at $FRAGMENTS_DIR"
        exit 1
    fi

    local git_short_hash
    git_short_hash=$(git -C "$EXAMPLES_DIR/.." rev-parse --short HEAD 2>/dev/null || echo "unknown")

    local count=0
    for frag_dir in "$FRAGMENTS_DIR"/*/; do
        [ -d "$frag_dir" ] || continue
        local frag_name
        frag_name=$(basename "$frag_dir")

        # Skip fragments with no .claude directory
        if [ ! -d "$frag_dir/.claude" ]; then
            echo "SKIP: $frag_name (no .claude directory)"
            continue
        fi

        local tracked_files
        tracked_files=$(get_tracked_files "$frag_dir")

        # Skip fragments with no tracked files
        if [ -z "$tracked_files" ]; then
            echo "SKIP: $frag_name (no tracked files)"
            continue
        fi

        local hash
        hash=$(compute_fragment_hash "$frag_dir")

        local marker_file="$frag_dir/.claude/.fragment"
        cat > "$marker_file" <<EOF
fragment=$frag_name
version=$git_short_hash
hash=$hash
tracked_files=$tracked_files
EOF

        echo "OK: $frag_name -> $marker_file (hash: ${hash:0:12}...)"
        count=$((count + 1))
    done

    echo "Generated $count marker(s)"
}

main "$@"
