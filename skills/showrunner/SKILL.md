---
name: showrunner
description: Keep the project's Obsidian vault (status board, decisions, versions, journal) in sync with the work. Use at the start of a session to get oriented, after finishing a task or getting the owner's verdict at a checkpoint, when the owner asks "what's the status", "what did we decide about X", "what did we do last week", or asks to log a decision, start or close a task. Requires .claude/showrunner.json in the project.
---

# Showrunner

The vault is the team's backlog and memory: status, owner decisions (including rejected options), version history, journal, IDs. Deliverables (texts, scripts, code, renders) stay in the repo; the vault only links to them.

Read `.claude/showrunner.json` for `vault` (path). Note content can be in any language; the service names below are fixed. Full protocol for every agent: the vault note `00 For agents.md`.

| What | Where |
|---|---|
| Status board | `Status.md` |
| Project hub | `Projects/<Project>/<Project>.md` |
| Journal | `Journal/YYYY-MM.md` |
| Task template | `Templates/Task.md` |
| Generated, never edit | `System/` |

## Reading — spend as few tokens as possible

1. The status board is injected at session start by the hook. If it isn't in context, read `Status.md`; don't list the vault.
2. For a task: the project hub, sections "Now" and "Decisions". Open a task note only when working on it.
3. To find a fact: Grep the vault (`files_with_matches`), then Read only the lines you need. If the Obsidian MCP server is connected: `vault_read` with `targetType: heading` and a path that starts with the H1, e.g. `["Teaser","Now"]`.
4. Never read `System/` to learn your own setup: the originals are at hand. Use `System/Sessions/` only to answer "what did we do with X".

## Writing — the main session owns status and decisions

After every finished task or owner checkpoint:

1. **Task note:** update "Now" and "Versions", frontmatter `status`, `updated`, `next`, and rewrite the folded `> [!summary]- Summary` callout at the top if the state changed. Every hub and task note has one: 2–3 sentences on what it is, where it stands, what's next.
2. **Decisions:** one line per owner verdict: `- DD.MM: what was decided — why`. Log rejected options too ("v04 rejected: too close to the reference") so nobody proposes them again.
3. **Status board:** one line per task, in the right section, linking the task note.
4. **Journal:** append `- DD.MM · <project> · <agent or —> · what was done → path`.

New task, video or product: create a note from `Templates/Task.md` in the project folder and add a line to the status board.

## Board and health check

Both are generated on every sync; never edit them.

- `System/Board.md`: the status board as a kanban for the owner. To move a card, edit `Status.md`.
- `System/Health.md`: stuck tasks (active, `updated` older than `health.stale_days`, default 7), broken links, missing `status`/`updated`/`next`, missing summary callout, active tasks absent from the status board. The issue count is injected at session start. When the owner asks for a review, or about once a week, read the report and fix the notes it names: refresh or close stuck tasks, fix links, add missing lines to the status board. Then tell the owner in a few lines what changed.

Subagents only append one journal line; they never edit the status board or hubs. When you delegate, pass the subagent the path of the task note.

Frontmatter values: `type: project | task`, `status: idea | in progress | waiting for owner | paused | done | rejected` (or your own vocabulary, listed in `health.active_statuses`), `updated: YYYY-MM-DD`, `next: one line`.

## Never

- Write anything into `System/`: the sync hook overwrites it.
- Put secrets (tokens, keys, passwords) in the vault: name the environment variable instead.
- Copy deliverables (post text, scripts, code) into the vault: link the file.
- Invent dates for past decisions: if unsure, write the decision without a date.
