"""Run: python -m unittest discover -s tests"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import fixture  # noqa: E402
import sync  # noqa: E402


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.project, self.home, self.tr = fixture.build(root)
        self.vault = root / "vault"
        self.vault.mkdir()
        self.system = self.vault / "System"

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, today="2026-11-05", *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sync.main(["--project", str(self.project), "--home", str(self.home),
                       "--transcripts", str(self.tr), "--today", today, *extra])
        return out.getvalue()

    def all_text(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in self.system.rglob("*.md"))

    def test_mirrors_setup(self):
        self.run_sync()
        for rel in ["Agents/researcher.md", "Agents/scriptwriter.md", "Agents/editor.md", "Agents.md",
                    "Skills.md", "Memory/pacing.md", "Memory.md",
                    "Rules/Rules — project (root).md", "Rules/Rules — Channel.md"]:
            self.assertTrue((self.system / rel).exists(), rel)
        self.assertIn("](Memory/pacing.md)", (self.system / "Memory.md").read_text(encoding="utf-8"))

    def test_past_months_fold_into_folders(self):
        self.run_sync("2026-11-05")
        sessions = self.system / "Sessions"
        self.assertEqual(sorted(p.name for p in sessions.glob("*.md")), ["2026-11-03 0a1b2c3d.md"])
        october = sorted(p.name for p in (sessions / "2026-10").glob("*.md"))
        self.assertIn("Sessions 2026-10.md", october)
        self.assertEqual(len(october), 3)
        index = (self.system / "Sessions.md").read_text(encoding="utf-8")
        self.assertIn("[[Sessions 2026-10]] — 2 sessions", index)

    def test_month_rollover_moves_notes_and_prunes(self):
        self.run_sync("2026-10-25")
        self.assertTrue((self.system / "Sessions" / "2026-10-06 0a1b2c3d.md").exists())
        self.run_sync("2026-11-05")
        self.assertFalse((self.system / "Sessions" / "2026-10-06 0a1b2c3d.md").exists())
        self.assertTrue((self.system / "Sessions" / "2026-10" / "2026-10-06 0a1b2c3d.md").exists())

    def test_secrets_and_noise_masked(self):
        self.run_sync()
        text = self.all_text()
        self.assertNotIn(fixture.FAKE_BOT_TOKEN, text)
        self.assertNotIn(fixture.FAKE_API_KEY, text)
        self.assertIn("<masked>", text)
        self.assertNotIn("noise that must not leak", text)

    def test_session_links_projects_and_agents(self):
        self.run_sync()
        note = (self.system / "Sessions" / "2026-10" / "2026-10-06 0a1b2c3d.md").read_text(encoding="utf-8")
        self.assertIn("[[Channel]]", note)
        self.assertIn("[[researcher]], [[scriptwriter]]", note)
        bot = (self.system / "Sessions" / "2026-10" / "2026-10-21 0a1b2c3d.md").read_text(encoding="utf-8")
        self.assertIn("[[Upload bot]]", bot)

    def test_no_home_paths_in_notes(self):
        self.run_sync()
        text = self.all_text()
        root = pathlib.Path(self.tmp.name).resolve()
        for p in (self.home, root):
            self.assertNotIn(str(p), text)
            self.assertNotIn(p.as_posix(), text)
        self.assertIn("~/.claude/projects/demo-project/", text)

    def test_hand_written_notes_survive(self):
        mine = self.system / "Agents" / "my-note.md"
        mine.parent.mkdir(parents=True)
        mine.write_text("# mine\n", encoding="utf-8")
        self.run_sync()
        self.assertTrue(mine.exists())

    def test_removed_agent_is_pruned(self):
        self.run_sync()
        (self.project / ".claude" / "agents" / "scriptwriter.md").unlink()
        self.run_sync()
        self.assertFalse((self.system / "Agents" / "scriptwriter.md").exists())

    def test_idempotent(self):
        self.run_sync()
        before = {p: p.stat().st_mtime_ns for p in self.system.rglob("*.md")}
        self.run_sync()
        after = {p: p.stat().st_mtime_ns for p in self.system.rglob("*.md")}
        self.assertEqual(before, after)

    def test_inject_status(self):
        (self.vault / "Status.md").write_text("---\ntype: status\n---\n\n# Status\n\n- thumbnail: waiting\n", encoding="utf-8")
        out = self.run_sync("2026-11-05", "--inject")
        self.assertIn("thumbnail: waiting", out)
        self.assertNotIn("type: status", out)

    def test_silent_without_inject(self):
        self.assertEqual(self.run_sync(), "")

    def test_no_config_does_nothing(self):
        (self.project / ".claude" / "showrunner.json").unlink()
        self.run_sync()
        self.assertFalse(self.system.exists())

    def test_russian_labels(self):
        cfg_path = self.project / ".claude" / "showrunner.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["lang"] = "ru"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        self.run_sync()
        self.assertTrue((self.vault / "Система" / "Сессии" / "2026-10" / "Сессии 2026-10.md").exists())
        self.assertTrue((self.vault / "Система" / "Правила" / "Правила — project (корень).md").exists())

    def write_vault(self, rel, text):
        p = self.vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_board_built_from_status(self):
        self.write_vault("Status.md", "# Status\n\n## Waiting for owner\n\n- **Channel** · thumbnail → [[Thumb]]\n- \n\n## In progress\n\n- render\n")
        self.run_sync()
        board = (self.system / "Board.md").read_text(encoding="utf-8")
        self.assertIn("kanban-plugin: board", board)
        self.assertIn("## Waiting for owner\n\n- [ ] **Channel** · thumbnail [[Thumb]]", board)
        self.assertIn("## In progress\n\n- [ ] render", board)
        self.assertNotIn("- [ ] \n", board)

    def test_health_report(self):
        self.write_vault("Status.md", "# Status\n\n## In progress\n\n- fresh → [[Fresh task]]\n")
        ok = "---\ntype: task\nstatus: in progress\nupdated: 2026-11-04\nnext: x\n---\n\n> [!summary]- Summary\n> ok\n\n# Fresh task\n"
        self.write_vault("Projects/Channel/Fresh task.md", ok)
        self.write_vault("Projects/Channel/Old task.md",
                         "---\ntype: task\nstatus: waiting for owner\nupdated: 2026-10-01\n---\n\n# Old\n\nSee [[Nowhere]] and `[[in code]]`.\n")
        self.run_sync("2026-11-05")
        report = (self.system / "Health.md").read_text(encoding="utf-8")
        old = "[[Old task]]"
        self.assertIn(f"{old}: 35", report)  # stale
        self.assertIn(f"{old} → `[[Nowhere]]`", report)  # broken link
        self.assertNotIn("in code", report)
        self.assertIn(f"{old}: next", report)  # missing field
        self.assertIn(f"- {old}\n", report)  # no summary callout
        self.assertIn(f"{old} (waiting for owner)", report)  # not on the board
        self.assertNotIn("[[Fresh task]]", report)

    def test_session_start_hook_injects(self):
        self.write_vault("Status.md", "# Status\n\n## Next\n\n- ride → [[Missing]]\n")
        out = io.StringIO()
        stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"hook_event_name": "SessionStart"}))
        try:
            with contextlib.redirect_stdout(out):
                sync.main(["--project", str(self.project), "--home", str(self.home), "--transcripts", str(self.tr),
                           "--today", "2026-11-05", "--hook"])
        finally:
            sys.stdin = stdin
        self.assertIn("- ride", out.getvalue())
        self.assertIn("Vault health: 1 to fix", out.getvalue())

    def test_mask_keeps_urls(self):
        url = "https://docs.google.com/spreadsheets/d/1" + "AbCdEfGhIjKlMnOpQrStUvWxYz_0123456789-abcd" + "/edit"
        self.assertEqual(sync.mask(url), url)


if __name__ == "__main__":
    unittest.main()
