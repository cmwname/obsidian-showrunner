---
name: setup
description: Set up Showrunner for the current project - connect an Obsidian vault, scaffold the status board, project hubs and agent protocol, wire CLAUDE.md and agents, run the first sync. Use when the user runs /showrunner:setup or asks to connect Obsidian as the team's backlog.
---

# Showrunner setup

Talk to the user in their language. Ask only what you can't detect. Never overwrite an existing file without showing it and asking.

## 1. Find the vault

- Obsidian keeps its vault list in `obsidian.json`: `%APPDATA%\obsidian\` (Windows), `~/Library/Application Support/obsidian/` (macOS), `~/.config/obsidian/` (Linux). Offer the vaults found there; otherwise ask for a folder (a new empty folder is fine, the user opens it in Obsidian later).
- Language for notes: `ru` if the user writes in Russian, else `en`. Other languages: use `en` note names, write content in the user's language.

## 2. Write `.claude/showrunner.json`

```json
{
  "vault": "<absolute path, forward slashes>",
  "lang": "en",
  "projects": { "<folder or unique substring in tool paths>": "<Project hub name>" },
  "rules": { "max_depth": 3, "exclude": [] },
  "mirror": { "agents": true, "skills": true, "rules": true, "memory": true, "sessions": true },
  "inject_status": true,
  "inject_limit": 4000,
  "board": true,
  "health": { "stale_days": 7 }
}
```

- `projects`: one entry per top-level folder that is a separate project. Sessions that touched it get linked to its hub. Ask the user to confirm the names.
- `rules.exclude`: folders with third-party `CLAUDE.md` files (cloned repos, examples).
- Add `.claude/.showrunner-cache.json` to `.gitignore` if the project uses git.

## 3. Scaffold the vault

Copy `${CLAUDE_PLUGIN_ROOT}/templates/vault/<lang>/` into the vault, skipping files that already exist. Then for each project in `projects`, create its hub from the task template (`type: project`) with sections Now, Decisions, Files. Fill what you already know from the repo (README, CLAUDE.md, recent files); leave the rest short. Don't invent history. Start every hub and task note with the folded summary callout from the template. Suggest the Kanban community plugin if the user wants the board as cards.

If the project already has a status/backlog file (`STATUS.md`, `TODO.md`, `backlog.md`), offer to move it: copy it into the vault's archive folder, rebuild the status board from it, and replace the original with a one-line pointer to the vault.

## 4. Wire Claude

- Append `${CLAUDE_PLUGIN_ROOT}/templates/snippets/<lang>/CLAUDE.md` to the project's `CLAUDE.md`, with the vault path filled in.
- Show the user `${CLAUDE_PLUGIN_ROOT}/templates/snippets/<lang>/agent.md` and offer to append it to their agents in `.claude/agents/` and `~/.claude/agents/`. Skip agents that already have it.
- If agents run with restricted tools or the vault is outside the project, suggest adding the vault to `permissions.additionalDirectories` in `.claude/settings.json`. The user approves settings changes themselves.

## 5. First sync and check

Run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" --inject` from the project root. Expect the status board printed and `System/` filled with agents, skills, rules, memory and sessions. Grep the generated session notes for anything that looks like a secret; if one slipped through, tell the user and add a pattern to `SECRETS` in `sync.py`.

Optional: the Obsidian MCP server (community plugin Local REST API) gives heading-level reads and frontmatter queries. Everything works without it.

Finish with a short summary: vault path, what was created, what the user should open first (`Home.md` / `00 Главная.md`).
