---
type: home
tags: [home]
---

# Home

Everything Claude does here: projects, status, decisions, the agent team, session history.

## Now

- [[Status]] — what's in progress and what waits for you
- [[Board]] — the same as a kanban (needs the Kanban community plugin; edit Status, not the board)
- [[Health]] — stuck tasks, broken links, missing fields
- [[Projects.base|Projects table]] — status, last update, next step
- Journal: one note per month in `Journal/`

## How the work is organised

- [[Team]] — agents, who hands what to whom, checkpoints
- [[Agents]] · [[Skills]] · [[Memory|What Claude remembers about you]]
- Rules: notes in `System/Rules/`
- [[Sessions|Session history]] — every conversation with Claude, your prompts in order
- [[00 For agents]] — how agents read and write this vault

## How it stays up to date

- Status, projects, tasks and the journal are kept by Claude as it works. Edit them by hand any time, Claude reads them.
- `System/` (agents, skills, rules, memory, sessions) is rebuilt by a hook at the start of every Claude session and after every answer. Don't edit it: the sources are `.claude/`, `~/.claude/` and `CLAUDE.md`.
