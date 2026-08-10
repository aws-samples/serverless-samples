# Hub Fragment Update

Review and apply updates from the central claude-hub fragment to the current project.

## Context

Fragment content in `CLAUDE.md` is delimited by markers:
```
<!-- claude-hub:fragment:begin — ... -->
(managed toolchain reference)
<!-- claude-hub:fragment:end — ... -->

(project-specific content below, never touched by updates)
```

Updates replace only the managed section between markers. Project-specific content below the end marker is preserved. Files under `.claude/` (settings, skills) are also fragment-managed and can be replaced directly.

## Steps

1. Read the `.claude/.fragment` marker file in the current project directory (`$PWD/.claude/.fragment`). If it does not exist, inform the developer that this project is not linked to a fragment and stop.

2. Parse the marker to extract `fragment` name and `tracked_files` list.

3. Locate the latest fragment source. Check `~/.claude/claude-hub/repo/examples/fragments/<fragment>/` first, then fall back to `~/.claude/claude-hub/repo/fragments/<fragment>/`. If neither exists, inform the developer that the fragment no longer exists in the central repo. Stop.

4. For each file in `tracked_files` (comma-separated):
   - **`.claude/*` files**: Compare project version with fragment version. Show diff if they differ.
   - **`CLAUDE.md`**: Extract the managed section (between `claude-hub:fragment:begin` and `claude-hub:fragment:end` markers) from both the project and the fragment source. Compare only those sections. Show diff if they differ.
   - If a file exists only in the fragment (new file), note it as available for addition.
   - If both exist and are identical, note as up to date.

5. Also check for any new files in the fragment's `.claude/` directory that are NOT in `tracked_files`.

6. Present a summary table of all files and their status. Ask the developer which files to update:
   - **All**: Apply all available updates
   - **Selective**: Choose per file
   - **Skip**: Cancel

7. Apply the selected updates:
   - **`.claude/*` files**: Replace the project file with the fragment version.
   - **`CLAUDE.md`**: Replace ONLY the content between `claude-hub:fragment:begin` and `claude-hub:fragment:end` markers. Preserve everything outside those markers (the markers themselves, and all project-specific content after the end marker). If markers are missing from the project file (developer removed them), warn and ask whether to prepend the managed section with markers at the top.

8. Recompute the fragment hash and update `.claude/.fragment`:
   - Find all files under `.claude/` (excluding `.fragment` itself), sort, concatenate with `---FILE:<path>---` delimiters.
   - Extract the managed section from the source fragment's `CLAUDE.md` and append as `---FILE:CLAUDE.md:managed---`.
   - Compute SHA-256 of the concatenated content.
   - Update the `hash`, `tracked_files`, and `version` fields.

9. Remove the drift notice file at `~/.claude/claude-hub/drift/` for this project (filename is MD5 of project path).

## Important

- Never modify content outside the fragment markers in `CLAUDE.md`.
- Never modify project files without explicit developer approval.
- Show diffs before applying any changes.
- If the cached repo does not exist, inform the developer to run a Claude Code session first so the sync script populates the cache.
