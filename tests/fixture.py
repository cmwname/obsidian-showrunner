"""A fictional studio used by the tests and to build examples/demo-vault.

Northwind Studio: a two-person YouTube channel about city cycling, run with
three Claude Code agents. Nothing here is real, including the "secrets".
"""
import json
import pathlib

FAKE_BOT_TOKEN = "123456789:AAH" + "x" * 32
FAKE_API_KEY = "sk-" + "demo" * 6

AGENT = """---
name: {name}
description: {desc}
tools: {tools}
---

You are the studio's {name}. Read the project CLAUDE.md first.
"""

SKILL = """---
name: {name}
description: {desc}
---

# {name}
"""


def user(ts, text):
    return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}


def agent_call(ts, subagent, path):
    return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Agent", "input": {"subagent_type": subagent, "prompt": f"Brief. Save to {path}"}}]}}


def edit(ts, path):
    return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": path}}]}}


SESSIONS = {
    "0a1b2c3d-1111-4111-8111-000000000001": [
        user("2026-10-06T08:02:11Z", "Let's start the channel. Research the top 5 myths about winter cycling, with sources."),
        agent_call("2026-10-06T08:03:40Z", "researcher", "channel/videos/2026-10-winter-myths/research.md"),
        user("2026-10-06T08:41:05Z", "Good. Myth 3 is weak, drop it and find one about studded tyres."),
        user("2026-10-06T09:15:30Z", "<system-reminder>noise that must not leak</system-reminder>Now a script, 8 minutes, hook in the first 5 seconds."),
        agent_call("2026-10-06T09:16:02Z", "scriptwriter", "channel/videos/2026-10-winter-myths/script.md"),
    ],
    "0a1b2c3d-2222-4222-8222-000000000002": [
        user("2026-10-21T17:00:00Z", f"Here is the bot token {FAKE_BOT_TOKEN} and the key {FAKE_API_KEY}, set up the upload bot."),
        edit("2026-10-21T17:05:00Z", "bot/main.py"),
        user("2026-10-21T17:30:00Z", "Works. Keep it on long polling for now."),
    ],
    "0a1b2c3d-3333-4333-8333-000000000003": [
        user("2026-11-03T10:00:00Z", "Thumbnail for the winter myths video: three options, bold type, no stock photos."),
        agent_call("2026-11-03T10:01:00Z", "editor", "channel/videos/2026-10-winter-myths/design/"),
        user("2026-11-03T11:20:00Z", "Option B. Make the snow less blue."),
    ],
}


def build(root):
    """Create project/ and home/ (with transcripts where Claude Code keeps them) under root."""
    root = pathlib.Path(root)
    project, home = root / "project", root / "home"
    tr = home / ".claude" / "projects" / "demo-project"

    files = {
        project / "CLAUDE.md": "# Northwind Studio\n\nYouTube channel about city cycling. Facts need a source and a date.\n",
        project / "channel" / "CLAUDE.md": "# Channel rules\n\nVideos 8-12 minutes, one idea per video, no stock footage.\n",
        project / "bot" / "README.md": "Upload bot. Token lives in .env as BOT_TOKEN.\n",
        project / ".claude" / "agents" / "researcher.md": AGENT.format(
            name="researcher", desc="Finds facts with sources for videos and posts.", tools="Read, Write, WebSearch, WebFetch"),
        project / ".claude" / "agents" / "scriptwriter.md": AGENT.format(
            name="scriptwriter", desc="Hooks, structure, script and shot list from the researcher's facts.", tools="Read, Write, Edit"),
        home / ".claude" / "agents" / "editor.md": AGENT.format(
            name="editor", desc="Edits video, motion graphics, thumbnails, renders.", tools="all"),
        home / ".claude" / "skills" / "thumbnail" / "SKILL.md": SKILL.format(
            name="thumbnail", desc="Bold-type YouTube thumbnails, three options per brief."),
        project / ".claude" / "showrunner.json": json.dumps({
            "vault": "../vault", "lang": "en",
            "projects": {"channel/": "Channel", "bot/": "Upload bot"},
        }, indent=2) + "\n",
        tr / "memory" / "MEMORY.md": "- [Pacing](pacing.md) — owner wants fast pacing, short pauses\n",
        tr / "memory" / "pacing.md": "---\nname: pacing\ndescription: owner wants fast pacing\nmetadata:\n  type: feedback\n---\n\nAround 160 words per minute, pauses under 0.3 s.\n",
    }
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for sid, events in SESSIONS.items():
        (tr / f"{sid}.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return project, home, tr
