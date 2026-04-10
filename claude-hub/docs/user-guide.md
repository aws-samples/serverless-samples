# Claude Hub: developer guide

Your organization uses Claude Hub to distribute Claude Code guidance to every developer. This guide covers what you get and how to use it.

## What is Claude Hub?

Claude Hub delivers your organization's standards, team conventions, and project-type guidance to Claude Code automatically. You don't install anything or maintain any configuration. It's deployed by your platform team and stays current on its own.

In practice, Claude Code already knows your org's coding standards and your team's conventions the moment you start a session. Skills like code review and security review work without setup. When standards change upstream, you get the update next time you start a session. If your project was scaffolded from a template, Claude Code also has project-type-specific context (toolchain commands, pre-approved permissions, deployment skills) from the first session.

This works alongside Claude Code's built-in plugin marketplace and any plugins you install yourself. Claude Hub handles your org's specific knowledge; the marketplace handles community and third-party plugins.

### How guidance reaches your machine

Claude Code reads instructions from three layers, each refining or overriding the previous:

1. **Organization standards**: coding standards, security policies, compliance requirements. Apply to everyone.
2. **Team conventions**: your team's tech stack, branching model, testing standards. Layer on top of org.
3. **Project-level**: the project CLAUDE.md, skills, and settings in the repository you're working in. Specific to that project. May come pre-configured via fragments if the project was scaffolded from a template.

How these get onto your machine is handled by your platform team. You don't need to configure anything.

## Getting started

### First-time setup

Your platform team may have already installed Claude Hub on your machine via MDM. If so, just start a Claude Code session.

If your org uses the manual setup (no MDM):

1. Clone the repo and run the setup script (ask your team lead which team name to use):
   ```bash
   git clone --depth=1 git@github.com:your-org/claude-hub.git ~/.claude/claude-hub/repo
   bash ~/.claude/claude-hub/repo/plugin/scripts/setup.sh --team your-team-name
   ```

2. Start a new Claude Code session. The sync runs automatically from now on.

**macOS users:** If you see `timeout: command not found` in `~/.claude/claude-hub/sync.log`, install GNU coreutils: `brew install coreutils`. The sync still works without it (falls back to cached files), but fetches won't have timeout protection.

### Verify it works

```bash
cat ~/.claude/CLAUDE.md     # User-level CLAUDE.md — should contain org and/or team instructions
ls ~/.claude/skills/        # Should show hub-* skills
```

## What you get

### Organization instructions

Claude Code follows your org's standards for code style, naming, code review, security, CI/CD, and deployment, as configured by your platform team.

### Team instructions

Your team's conventions layer on top of org standards. This covers tech stack and framework preferences, branching strategy, testing standards, and any team-specific overrides.

### MCP servers

Your org and team may configure MCP servers that give Claude Code access to external tools like Jira, internal knowledge bases, and artifact registries. The configs sync to your machine like everything else and show up when you start a session.

If an MCP server requires authentication (a Jira instance behind SSO, for example), your platform team will provide credential setup instructions separately.

### Plugins and marketplaces

Your org may pre-register a private plugin marketplace and auto-enable internal plugins. These show up next to any community plugins you install yourself from the built-in marketplace.

Pre-configured plugins are enabled automatically. You can see them with `/plugin list` and manage them normally (disable, update, etc.). If your org maintains a private marketplace, you can browse it with `/plugin marketplace list` and install additional plugins from it.

If plugin auto-updates require authentication to a private repository, your platform team will provide instructions for setting up a token (typically a `GITHUB_TOKEN` or similar in your shell environment).

### Skills

Skills are reusable prompts you run with a slash command. There are three levels.

**Org skills** (available to everyone, prefixed with `hub-`):

```
/hub-code-standards       Review code against org coding standards
/hub-security-review      Run a security review of changes
```

**Team skills** (available to your team only, also prefixed with `hub-`):

```
/hub-api-design           Review REST API design, pagination, auth
/hub-load-test            Generate load test scripts
/hub-component-review     Review components for accessibility, performance
```

**Project skills** (available only in a specific project). These come from the project's `.claude/skills/` directory (shipped via fragments) and have no prefix:

```
/deploy                   Validate, plan, and apply this Terraform configuration
/api-test                 Run integration tests against the deployed API
```

Type `/hub-` in Claude Code to see all available org and team skills. Type `/` and browse to see project skills.

## Day-to-day usage

### It's automatic

Every time you start a Claude Code session, the sync script checks for updates and applies them. If you're offline, it uses the last cached version.

### Switching teams

If you move to a different team:

```bash
echo "new-team-name" > ~/.claude/claude-hub/team
```

Start a new Claude Code session to pick up the new team's configuration.

### About the user-level ~/.claude/CLAUDE.md

The hub writes to the user-level `~/.claude/CLAUDE.md` with your org and team configuration. Don't edit this file manually. It gets overwritten on each sync.

You can still use project-level CLAUDE.md files in your repositories. Those are separate and unaffected by hub sync.

## Working with the project CLAUDE.md

Skip this section if your project wasn't created from a scaffolding template (Backstage, Cookiecutter, etc.).

Scaffolded projects come with a project CLAUDE.md and a `.claude/` directory pre-configured. This gives Claude Code project-specific context from the first session.

### What's in a scaffolded project

When you create a project from a template, it includes:

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project CLAUDE.md: toolchain reference (managed section) + your project notes (yours to edit) |
| `.claude/settings.json` | Pre-approved permissions (e.g., `terraform plan`, `pytest`, `curl`) |
| `.claude/skills/` | Project-type-specific skills (e.g., `deploy`, `api-test`) |
| `.claude/.fragment` | Version marker for drift detection |

The project CLAUDE.md has two zones separated by markers:

```markdown
<!-- claude-hub:fragment:begin — This section is managed centrally. Do not edit manually. Run /hub-fragment-update to update. -->
# Terraform Service — Toolchain Reference
... (toolchain commands, patterns, pitfalls) ...
<!-- claude-hub:fragment:end — Add your project-specific content below this line. -->

# Project Notes
Add your content here...
```

### Using project skills

Scaffolded projects include skills tailored to that project type (listed in the table above). These skills know about the project's structure and toolchain. For example, a deploy skill might validate, test, plan, and apply in sequence.

### Fragment updates

The platform team may update the toolchain reference (new commands, updated pitfalls, improved patterns). When this happens, the sync script detects the difference on your next session start and shows a notice.

To review and apply:

```
/hub-fragment-update
```

This shows a diff of each changed file, lets you pick which updates to apply, and replaces only the managed section between the markers. Your content below the end marker is never touched. Files in `.claude/` (settings, skills) can also be updated this way.

### Adding your own project context

After scaffolding, fill in the project notes section of the project CLAUDE.md. Write down architecture decisions (and why you made them), key database patterns, environment-specific setup steps, and pitfalls you've hit. The more concrete you are, the less Claude Code has to guess.

## Troubleshooting

**Claude Code doesn't seem to know our standards**
Check that the sync is set up. Depending on how your org deployed Claude Hub, the hook lives in one of two places:
```bash
# MDM installs -- hook comes from the plugin:
ls ~/.claude/plugins/local/claude-hub/hooks/hooks.json

# Manual installs -- hook is in settings.json:
cat ~/.claude/settings.json | python3 -c "import sys,json; h=json.load(sys.stdin).get('hooks',{}); print('SessionStart hook:', 'found' if 'SessionStart' in h else 'MISSING')"
```
If neither exists, follow the setup steps above or ask your platform team.

**My team's conventions aren't showing up**
Check your team file:
```bash
cat ~/.claude/claude-hub/team
```
If it's empty or wrong, set it and restart Claude Code.

**Skills aren't available**
Start a new Claude Code session. Skills are copied during sync. Type `/hub-` and see if any appear.

**Configuration seems stale**
The sync caches for 5 minutes. Close and reopen Claude Code. If it persists:
```bash
cat ~/.claude/claude-hub/sync.log
```

**Working offline**
Claude Hub works offline using cached files from the last successful sync. You won't get updates until you're back online, but nothing breaks.

## FAQ

**Can I override org standards for my project?**
Yes. Put project-specific instructions in your repository's project CLAUDE.md (below the fragment end marker if the project uses fragments). Claude Code reads both the user-level `~/.claude/CLAUDE.md` and the project CLAUDE.md, and the project-level file takes precedence for that project.

**Can I add my own skills?**
Yes. Create skill directories under `~/.claude/skills/` for personal skills, or under your project's `.claude/skills/` for project-specific skills. Don't use the `hub-` prefix, which is reserved for synced skills.

**What's the difference between hub skills and project skills?**
Hub skills (`/hub-*`) come from the central claude-hub repo and are synced to your machine. They cover org-wide and team-wide concerns (code review, security, standards). Project skills (no prefix) live in the project's `.claude/skills/` directory and are specific to that project type (deploy, test, inspect). Both are available as slash commands.

**My project was created from a template but has no `.claude/` directory**
The template may predate the fragment system. Ask your platform team for the correct fragment name, then copy it from the hub repo. For example, if the fragment is `python-lambda`:
```bash
cp -r ~/.claude/claude-hub/repo/examples/fragments/python-lambda/.claude .
cp ~/.claude/claude-hub/repo/examples/fragments/python-lambda/CLAUDE.md .
```

**Will hub sync overwrite my personal settings?**
The hub manages the user-level `~/.claude/CLAUDE.md`, `~/.claude/skills/hub-*`, and specific entries it placed in `~/.claude/settings.json` (MCP servers, marketplace registrations, and enabled plugins). It tracks which entries it added and only touches those; your own settings, servers, and personally installed plugins are left alone. Project-level `.claude/` files are never modified by hub sync.

**What about plugins I installed myself?**
Plugins you install from the community marketplace or any other source are yours. Hub-distributed plugins and marketplace registrations are additive and don't interfere with your personal plugin choices. If a hub-distributed plugin conflicts with one you installed, you can disable either one with `/plugin disable`.

