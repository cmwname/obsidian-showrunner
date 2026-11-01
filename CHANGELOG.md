# Changelog

## 0.1.0 — 2026-11-01

First public version.

- Status board injected at session start; mirror sync after every answer.
- Mirror of agents, skills, `CLAUDE.md` rules, auto-memory and session history into `System/`.
- Session notes with masked secrets; past months folded into `Sessions/YYYY-MM/`.
- Skills: `showrunner` (read/write protocol), `setup` (`/showrunner:setup`).
- Vault templates and snippets in English and Russian.
- Kanban view `System/Board.md`, generated from the status board (Obsidian Kanban plugin format).
- Health report `System/Health.md`: stuck tasks, broken links, missing fields and summaries, active tasks off the board; issue count injected at session start.
- Folded summary callout at the top of every hub and task note.
- Status board injected on any SessionStart hook event, not only with `--inject`.
- Demo vault of a fictional studio, 17 unit tests.

Board, summary and health check were adopted after trying the vault against obsidian-second-brain's conventions.
