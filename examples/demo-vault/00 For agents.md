---
type: protocol
tags: [protocol]
---

# For agents: how to use this vault

This vault is the team's backlog and memory: status, owner decisions, version history, journal, IDs. Deliverables (texts, scripts, code, renders) live in the project repo; here we only link to them.

Files on disk are always readable, so use Read and Grep by default. The Obsidian MCP server, if connected, only answers while Obsidian is open.

## Read cheaply

1. Main session: the status board is injected at session start. Otherwise read `Status.md` and nothing else first.
2. Working on a project: its hub `Projects/<Project>/<Project>.md`, sections "Now" and "Decisions". Open a task note only if you work on that task. Every hub and task starts with a folded `Summary` callout: read those 2–3 lines first and stop if the note isn't relevant.
3. Looking for a fact: Grep the vault with `files_with_matches`, then Read only the lines you need. Via MCP: `search_simple`, then `vault_read` with `targetType: heading` and a path that starts with the H1, e.g. `["Teaser","Now"]`.
4. IDs of external files, render commands, tools: `Reference/`.
5. `System/` is an auto-generated mirror of agents, skills, rules, memory and sessions, for the owner. You don't need it: the originals are at hand. Exception: session history, when the owner asks "what did we do about…".
6. Project rules: read the original `CLAUDE.md` in the repo.

## Write

- **Subagent:** save results in the repo as usual. In the vault, only append one line to this month's journal `Journal/YYYY-MM.md`: `- DD.MM · <project> · <agent> · what was done → path`. Don't touch the status board or hubs.
- **Main session**, after every finished task or owner checkpoint:
  - update the task's line in `Status.md`;
  - in the task note, update "Now" and "Versions", and frontmatter `status`, `updated`, `next`;
  - add the owner's verdict to "Decisions": date, what was decided, why. Rejected options too, so nobody proposes them again;
  - rewrite the `Summary` callout if the task's state changed.
- `System/Board.md` (kanban) is built from `Status.md`, `System/Health.md` lists stuck tasks, broken links, missing fields and active tasks missing from the board. Both rebuild on every sync. The count of issues shows up at session start; fix them in the notes, about once a week.
- New task, video or product: a note from `Templates/Task.md` in the project folder, plus a line in `Status.md`.
- Never write into `System/`: the sync overwrites it.
- Never put secrets (tokens, keys, passwords) in the vault. Name the environment variable instead.
- Keep it short: lists, paths in `code`, links to notes. Don't copy posts, scripts or code here, link the file.

## Note properties

```yaml
type: project | task
project: Studio            # hub name
status: idea | in progress | waiting for owner | paused | done | rejected
updated: 2026-11-01
next: what to do next, one line
```

Find by status: Grep `status: waiting for owner` in `Projects/`, or MCP `search_query` with `{"==":[{"var":"frontmatter.status"},"waiting for owner"]}`.
