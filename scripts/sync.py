"""Showrunner sync: mirror a Claude Code setup into an Obsidian vault.

Copies agents, skills, CLAUDE.md rules, auto-memory and session history into
the vault's System/ folder, writing a file only when its content changed.
Silent on success: as a SessionStart hook, anything printed lands in context.
With --inject it prints the vault's status board instead, on purpose.

Config: <project>/.claude/showrunner.json. No config -> does nothing.
Standard library only, Python 3.8+.
"""
import argparse
import datetime
import fnmatch
import json
import os
import pathlib
import re
import sys

LABELS = {
    "en": {
        "system": "System", "agents": "Agents", "skills": "Skills", "rules": "Rules",
        "memory": "Memory", "sessions": "Sessions", "status": "Status", "team": "Team",
        "root": "root", "global": "Global", "rules_prefix": "Rules",
        "banner": "Auto-copy, edits here get overwritten. Source:",
        "agents_title": "Agents", "agents_intro": "Who does what and how they hand off work: [[{team}]].",
        "agents_cols": "| Agent | Scope | Tools |", "scope_project": "project", "scope_global": "global",
        "tools_all": "all", "model_default": "default", "where": "Lives in", "tools": "Tools",
        "team_link": "Team map", "prompt": "Agent prompt",
        "skills_title": "Skills", "skills_cols": "| Skill | Scope | Purpose | Folder |",
        "memory_title": "What Claude remembers",
        "s_title": "Claude session history", "s_intro": "Secrets in prompts are masked. Past months are folded into monthly folders.",
        "s_cols": "| Started (UTC) | Session | Projects | Agents | Prompts |",
        "s_none": "No sessions yet.", "s_past": "Past months", "s_count": "{n} sessions",
        "s_month_intro": "{n} sessions, newest first. All sessions: [[{index}]].",
        "s_time": "Time", "s_projects": "Projects", "s_agents": "Agents", "s_prompts": "Owner prompts",
        "s_requests": "Owner requests", "inject": "Showrunner status board ({path}). Detail lives in the linked notes:",
        "projects": "Projects", "summary": "Summary", "board": "Board", "health": "Health",
        "board_note": "Kanban view of [[{status}]], rebuilt on every sync. Edit the status board, not this file.",
        "h_title": "Vault health", "h_intro": "Rebuilt on every sync ({date}). Fix the notes, not this report.",
        "h_clean": "All clean.", "h_total": "{n} to fix",
        "h_stale": "Stuck: active, not updated for more than {days} days",
        "h_links": "Broken links", "h_fields": "Missing status / updated / next",
        "h_summary": "No summary callout", "h_offboard": "Active tasks missing from the status board",
        "h_inject": "Vault health: {n} to fix → {path}",
        "active": ["in progress", "waiting for owner"], "closed": ["done", "rejected", "paused", "idea"],
    },
    "ru": {
        "system": "Система", "agents": "Агенты", "skills": "Скиллы", "rules": "Правила",
        "memory": "Память", "sessions": "Сессии", "status": "Статус", "team": "Команда",
        "root": "корень", "global": "Глобальные", "rules_prefix": "Правила",
        "banner": "Автокопия, правки здесь затрутся. Источник:",
        "agents_title": "Агенты", "agents_intro": "Кто что делает и как взаимодействуют: [[{team}]].",
        "agents_cols": "| Агент | Где | Инструменты |", "scope_project": "проект", "scope_global": "глобальный",
        "tools_all": "все", "model_default": "по умолчанию", "where": "Где живёт", "tools": "Инструменты",
        "team_link": "Схема команды", "prompt": "Промпт агента",
        "skills_title": "Скиллы", "skills_cols": "| Скилл | Где | Для чего | Папка |",
        "memory_title": "Что Claude помнит о владельце",
        "s_title": "История сессий Claude", "s_intro": "Секреты в запросах замаскированы. Прошлые месяцы сложены в папки по месяцам.",
        "s_cols": "| Начало (UTC) | Сессия | Проекты | Агенты | Запросов |",
        "s_none": "Сессий пока нет.", "s_past": "Прошлые месяцы", "s_count": "{n} сессий",
        "s_month_intro": "{n} сессий. Новые сверху. Все сессии — [[{index}]].",
        "s_time": "Время", "s_projects": "Проекты", "s_agents": "Агенты", "s_prompts": "Сообщений владельца",
        "s_requests": "Запросы владельца", "inject": "Доска статуса Showrunner ({path}). Детали в заметках по ссылкам:",
        "projects": "Проекты", "summary": "Кратко", "board": "Доска", "health": "Проверка",
        "board_note": "Канбан-вид [[{status}]], пересобирается при каждой синхронизации. Править «Статус», а не этот файл.",
        "h_title": "Проверка хранилища", "h_intro": "Пересобирается при каждой синхронизации ({date}). Править заметки, а не этот отчёт.",
        "h_clean": "Всё чисто.", "h_total": "замечаний: {n}",
        "h_stale": "Застряли: активны, не обновлялись больше {days} дн.",
        "h_links": "Битые ссылки", "h_fields": "Нет status / updated / next",
        "h_summary": "Нет блока «Кратко»", "h_offboard": "Активные задачи, которых нет в «Статусе»",
        "h_inject": "Проверка хранилища: замечаний {n} → {path}",
        "active": ["в работе", "ждёт владельца"], "closed": ["готово", "отклонено", "пауза", "идея"],
    },
}

SECRETS = [
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),  # Telegram bot token
    re.compile(r"\bAQVN[A-Za-z0-9_-]{20,}"),  # Yandex Cloud API key
    re.compile(r"\by0_[A-Za-z0-9_-]{20,}"),  # Yandex OAuth
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),  # AWS access key id
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),  # Google API key
    re.compile(r"\b(sk|pk|rk|ghp|gho|ghs|github_pat|xox[abpr])[-_][A-Za-z0-9_-]{16,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?<![/=?&#A-Za-z0-9_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])"),  # long blob outside URLs
]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".obsidian"}
NOISE = re.compile(r"<(system-reminder|ide_selection|ide_opened_file|local-command-[a-z]+|command-[a-z]+)>.*?</\1>", re.S)


def mask(text):
    for rx in SECRETS:
        text = rx.sub("<masked>", text)
    return text


class Sync:
    def __init__(self, project, vault, home, transcripts, cfg, today):
        self.project, self.vault, self.home, self.transcripts = project, vault, home, transcripts
        self.cfg, self.today = cfg, today
        self.L = LABELS.get(cfg.get("lang", "en"), LABELS["en"])
        self.root = vault / self.L["system"]
        self.projects = cfg.get("projects", {})
        self.written = set()
        self.issues = 0

    # ---------- helpers

    def shown(self, path):
        """Path as shown in notes: ./ for the project, ~/ for home. Keeps usernames out of the vault."""
        path = pathlib.Path(path)
        for base, prefix in ((self.project, "."), (self.home, "~")):
            try:
                return prefix + "/" + path.resolve().relative_to(base.resolve()).as_posix()
            except ValueError:
                pass
        return path.as_posix()

    def write(self, rel, body):
        path = self.root / rel
        self.written.add(path.resolve())
        if path.exists() and path.read_text(encoding="utf-8") == body:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def header(self, source, tags, extra=None):
        fm = {"generated": True, "source": source, "tags": tags}
        fm.update(extra or {})
        lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()]
        lines += ["---", "", f"> [!info] {self.L['banner']} `{source}`", "", ""]
        return "\n".join(lines)

    @staticmethod
    def frontmatter(text):
        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
        if not m:
            return {}, text
        meta = {}
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(":")
            if sep and not line.startswith((" ", "\t")):
                meta[k.strip()] = v.strip().strip('"')
        return meta, text[m.end():]

    def project_name(self, folder):
        return self.projects.get(folder) or self.projects.get(folder + "/") or folder

    # ---------- mirrors

    def agents(self):
        L, rows = self.L, []
        for d, scope in ((self.project / ".claude" / "agents", L["scope_project"]),
                         (self.home / ".claude" / "agents", L["scope_global"])):
            for f in sorted(d.glob("*.md")):
                meta, body = self.frontmatter(f.read_text(encoding="utf-8"))
                name = meta.get("name", f.stem)
                tools = meta.get("tools", L["tools_all"])
                extra = {"agent": name, "scope": scope, "tools": tools, "model": meta.get("model", L["model_default"])}
                note = self.header(self.shown(f), ["agent"], extra)
                note += (f"# {name}\n\n{meta.get('description', '')}\n\n- {L['tools']}: {tools}\n- {L['where']}: {scope}\n"
                         f"- {L['team_link']}: [[{L['team']}]]\n\n## {L['prompt']}\n\n{mask(body.strip())}\n")
                self.write(f"{L['agents']}/{name}.md", note)
                rows.append(f"| [[{name}]] | {scope} | {tools} |")
        self.write(f"{L['agents']}.md", self.header("./.claude/agents + ~/.claude/agents", ["agent", "index"])
                   + f"# {L['agents_title']}\n\n{L['agents_intro'].format(team=L['team'])}\n\n{L['agents_cols']}\n|---|---|---|\n"
                   + "\n".join(rows) + "\n")

    def skills(self):
        L, rows = self.L, []
        roots = [(self.project / ".claude" / "skills", L["scope_project"]),
                 (self.home / ".claude" / "skills", L["scope_global"])]
        for root, scope in roots:
            for f in sorted(root.glob("*/SKILL.md")) + sorted(root.glob("*/*/SKILL.md")):
                meta, _ = self.frontmatter(f.read_text(encoding="utf-8"))
                desc = re.sub(r"\s+", " ", meta.get("description", "")).replace("|", "/")
                desc = desc if len(desc) <= 180 else desc[:177] + "..."
                rows.append(f"| `{meta.get('name', f.parent.name)}` | {scope} | {desc} | `{self.shown(f.parent)}` |")
        self.write(f"{L['skills']}.md", self.header("./.claude/skills + ~/.claude/skills", ["skill", "index"])
                   + f"# {L['skills_title']}\n\n{L['skills_cols']}\n|---|---|---|---|\n" + "\n".join(rows) + "\n")

    def rule_files(self):
        rcfg = self.cfg.get("rules", {})
        depth, exclude = rcfg.get("max_depth", 3), rcfg.get("exclude", [])
        found = []
        for dirpath, dirnames, filenames in os.walk(self.project):
            rel = pathlib.Path(dirpath).relative_to(self.project)
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                           and not any(fnmatch.fnmatch((rel / d).as_posix(), p.rstrip("/*")) for p in exclude)]
            if len(rel.parts) >= depth:
                dirnames[:] = []
            if "CLAUDE.md" in filenames:
                found.append(pathlib.Path(dirpath) / "CLAUDE.md")
        return found

    def rules(self):
        L = self.L
        for f in self.rule_files():
            rel = f.parent.relative_to(self.project)
            title = f"{self.project.name} ({L['root']})" if not rel.parts else self.project_name(rel.as_posix())
            self.write(f"{L['rules']}/{L['rules_prefix']} — {title}.md",
                       self.header(self.shown(f), ["rules"]) + mask(f.read_text(encoding="utf-8")))
        g = self.home / ".claude" / "CLAUDE.md"
        if g.exists():
            self.write(f"{L['rules']}/{L['rules_prefix']} — {L['global']}.md",
                       self.header(self.shown(g), ["rules"]) + mask(g.read_text(encoding="utf-8")))

    def memory(self):
        L, d = self.L, self.transcripts / "memory"
        for f in sorted(d.glob("*.md")):
            if f.name == "MEMORY.md":
                continue
            meta, body = self.frontmatter(f.read_text(encoding="utf-8"))
            self.write(f"{L['memory']}/{f.stem}.md", self.header(self.shown(f), ["memory"], {"memory_type": meta.get("type", "")})
                       + f"# {meta.get('name', f.stem)}\n\n_{meta.get('description', '')}_\n\n{mask(body.strip())}\n")
        idx = d / "MEMORY.md"
        if idx.exists():
            text = re.sub(r"\]\(([^)]+)\.md\)", lambda m: f"]({L['memory']}/{m.group(1)}.md)", idx.read_text(encoding="utf-8"))
            self.write(f"{L['memory']}.md", self.header(self.shown(idx), ["memory", "index"]) + f"# {L['memory_title']}\n\n" + mask(text))

    # ---------- sessions

    def parse_session(self, f):
        first = last = None
        prompts, agents_used, projects = [], set(), set()
        with f.open(encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        for line in lines:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if ts:
                first, last = first or ts, ts
            if e.get("type") == "assistant":
                for c in (e.get("message") or {}).get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        if c.get("name") in ("Agent", "Task"):
                            agents_used.add(inp.get("subagent_type") or "general-purpose")
                        blob = json.dumps(inp, ensure_ascii=False)
                        projects.update(hub for key, hub in self.projects.items() if key in blob)
                continue
            if e.get("type") != "user" or e.get("isSidechain") or e.get("isMeta"):
                continue
            m = (e.get("message") or {}).get("content")
            if isinstance(m, list):
                m = " ".join(c.get("text", "") for c in m if isinstance(c, dict) and c.get("type") == "text")
            if not isinstance(m, str):
                continue
            m = re.sub(r"\s+", " ", NOISE.sub("", m)).strip()
            if not m or m.startswith(("[Request interrupted", "<", "This session is being continued")):
                continue
            prompts.append(mask(m if len(m) <= 300 else m[:297] + "..."))
        return {"first": first, "last": last, "prompts": prompts,
                "agents": sorted(agents_used), "projects": sorted(projects)}

    def sessions(self, cache):
        L = self.L
        this_month = self.today.strftime("%Y-%m")
        rows = {}
        for f in self.transcripts.glob("*.jsonl"):
            st = f.stat()
            key = f"{st.st_mtime_ns}:{st.st_size}"
            s = cache.get(f.stem)
            if not s or s.get("key") != key:
                s = self.parse_session(f)
                s["key"] = key
                cache[f.stem] = s
            if not s["first"] or not s["prompts"]:
                continue
            day, name = s["first"][:10], f"{s['first'][:10]} {f.stem[:8]}"
            month = day[:7]
            title = s["prompts"][0][:90]
            links = ", ".join(f"[[{p}]]" for p in s["projects"]) or "—"
            ag = ", ".join(f"[[{a}]]" for a in s["agents"]) or "—"
            extra = {"session": f.stem, "start": s["first"], "end": s["last"], "prompts": len(s["prompts"]),
                     "projects": s["projects"], "agents": s["agents"]}
            body = self.header(self.shown(f), ["session"], extra)
            body += (f"# {title}\n\n- {L['s_time']}: {s['first'][:16].replace('T', ' ')} → {s['last'][:16].replace('T', ' ')} UTC\n"
                     f"- {L['s_projects']}: {links}\n- {L['s_agents']}: {ag}\n- {L['s_prompts']}: {len(s['prompts'])}\n\n"
                     f"## {L['s_requests']}\n\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(s["prompts"], 1)) + "\n")
            # Current month: loose notes. Past months: folded into Sessions/YYYY-MM/.
            folder = L["sessions"] if month == this_month else f"{L['sessions']}/{month}"
            self.write(f"{folder}/{name}.md", body)
            row = f"| {s['first'][:16].replace('T', ' ')} | [[{name}\\|{title[:70]}]] | {links} | {ag} | {len(s['prompts'])} |"
            rows.setdefault(month, []).append((s["first"], row))
        table = L["s_cols"] + "\n|---|---|---|---|---|\n"
        archive = []
        for month in sorted((m for m in rows if m != this_month), reverse=True):
            items = sorted(rows[month], reverse=True)
            n = len(items)
            self.write(f"{L['sessions']}/{month}/{L['sessions']} {month}.md",
                       self.header(self.shown(self.transcripts), ["session", "index"], {"month": month})
                       + f"# {L['sessions']} {month}\n\n{L['s_month_intro'].format(n=n, index=L['sessions'])}\n\n"
                       + table + "\n".join(r for _, r in items) + "\n")
            archive.append(f"- [[{L['sessions']} {month}]] — {L['s_count'].format(n=n)}")
        current = sorted(rows.get(this_month, []), reverse=True)
        self.write(f"{L['sessions']}.md", self.header(self.shown(self.transcripts), ["session", "index"])
                   + f"# {L['s_title']}\n\n{L['s_intro']}\n\n## {this_month}\n\n"
                   + (table + "\n".join(r for _, r in current) if current else L["s_none"]) + "\n\n"
                   + f"## {L['s_past']}\n\n" + ("\n".join(archive) or "—") + "\n")

    # ---------- views over the hand-written notes

    def status_sections(self):
        """[(column title, [item text])] from the status board's H2 sections and top-level bullets."""
        status = self.vault / f"{self.L['status']}.md"
        if not status.exists():
            return []
        _, body = self.frontmatter(status.read_text(encoding="utf-8"))
        cols = []
        for line in body.splitlines():
            if line.startswith("## "):
                cols.append((line[3:].strip(), []))
            elif cols and re.match(r"^[-*] \S", line):
                cols[-1][1].append(line[2:].strip())
        return cols

    def board(self):
        """Kanban (Obsidian Kanban plugin format) built from the status board. Without the plugin it reads as checklists."""
        L, cols = self.L, self.status_sections()
        if not cols:
            return
        fm = ["---", "generated: true", "kanban-plugin: board", f"source: {json.dumps(L['status'] + '.md', ensure_ascii=False)}",
              "tags: [\"board\"]", "---", ""]
        out = []
        for title, items in cols:
            out += [f"## {title}", ""] + [f"- [ ] {item.replace(' → ', ' ')}" for item in items] + [""]
        out += [f"%% {L['board_note'].format(status=L['status'])} %%", "",
                "%% kanban:settings", "```", '{"kanban-plugin":"board","show-checkboxes":false}', "```", "%%", ""]
        self.write(f"{L['board']}.md", "\n".join(fm + out))

    def notes(self):
        """Hand-written notes: everything outside System/ and the templates folder."""
        skip = {self.L["system"], "Templates", "Шаблоны", ".obsidian", ".claude", ".trash"}
        for p in self.vault.rglob("*.md"):
            rel = p.relative_to(self.vault)
            if not skip.intersection(rel.parts[:1]):
                yield rel, p.read_text(encoding="utf-8")

    def health(self):
        L, hcfg = self.L, self.cfg.get("health", {})
        days = int(hcfg.get("stale_days", 7))
        names = {p.stem for p in self.vault.rglob("*.md")} | {p.name for p in self.vault.rglob("*") if p.suffix in (".base", ".canvas")}
        names |= {pathlib.Path(r).stem for r in self.written} | {L["health"]}  # this report isn't written yet
        status_links = set()
        for _, items in self.status_sections():
            for item in items:
                status_links.update(re.split(r"[#|]", m)[0].strip() for m in re.findall(r"\[\[([^\]]+)\]\]", item))
        found = {k: [] for k in ("stale", "links", "fields", "summary", "offboard")}
        for rel, text in self.notes():
            link = f"[[{rel.stem}]]"
            plain = re.sub(r"```.*?```|`[^`\n]*`", "", text, flags=re.S)
            for target in re.findall(r"\[\[([^\]]+)\]\]", plain):
                t = re.split(r"[#|]", target)[0].rstrip("\\").strip()
                if t and pathlib.PurePosixPath(t).name not in names and pathlib.PurePosixPath(t).stem not in names:
                    found["links"].append(f"{link} → `[[{t}]]`")
            if rel.parts[0] != L["projects"]:
                continue
            meta, body = self.frontmatter(text)
            status = meta.get("status", "").strip()
            missing = [k for k in ("status", "updated", "next") if not meta.get(k, "").strip()]
            if missing:
                found["fields"].append(f"{link}: {', '.join(missing)}")
            if not re.search(r"^> \[!(summary|abstract|tldr|info)\]", body, re.M | re.I):
                found["summary"].append(link)
            if status in L["active"]:
                try:
                    age = (self.today - datetime.date.fromisoformat(meta.get("updated", "")[:10])).days
                except ValueError:
                    age = None
                if age is not None and age > days:
                    found["stale"].append(f"{link}: {age}")
                if rel.stem not in status_links and meta.get("type") not in ("project", "проект"):
                    found["offboard"].append(f"{link} ({status})")
        total = sum(len(v) for v in found.values())
        out = [self.header(f"./{L['status']}.md + {L['projects']}/", ["health"], {"issues": total}),
               f"# {L['h_title']}", "", L["h_intro"].format(date=self.today.isoformat()), "",
               f"**{L['h_total'].format(n=total)}**" if total else L["h_clean"], ""]
        titles = {"stale": L["h_stale"].format(days=days), "links": L["h_links"], "fields": L["h_fields"],
                  "summary": L["h_summary"], "offboard": L["h_offboard"]}
        for key, items in found.items():
            if items:
                out += [f"## {titles[key]}", ""] + [f"- {i}" for i in sorted(set(items))] + [""]
        self.write(f"{L['health']}.md", "\n".join(out))
        self.issues = total

    def prune(self):
        """Delete generated notes that were not written this run (moved, renamed, removed at source)."""
        for f in self.root.rglob("*.md"):
            if f.resolve() not in self.written and "generated: true" in f.read_text(encoding="utf-8")[:300]:
                f.unlink()
        for d in sorted((p for p in self.root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()

    def run(self, cache_path):
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
        mirror = self.cfg.get("mirror", {})
        steps = [s for s in ("agents", "skills", "rules", "memory", "sessions") if mirror.get(s, True)]
        # Views run last: health checks links against everything written above.
        steps += [v for v in ("board", "health") if self.cfg.get(v, True) is not False]
        ok = True
        for step in steps:
            try:
                getattr(self, step)(cache) if step == "sessions" else getattr(self, step)()
            except Exception as exc:  # one broken part must not stop the others
                ok = False
                print(f"showrunner: {step}: {exc}", file=sys.stderr)
        if ok:  # otherwise we'd delete notes of a step that didn't finish
            self.prune()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    def inject(self):
        status = self.vault / f"{self.L['status']}.md"
        if not status.exists():
            return
        _, body = self.frontmatter(status.read_text(encoding="utf-8"))
        limit = int(self.cfg.get("inject_limit", 4000))
        body = body.strip()
        if len(body) > limit:
            body = body[:limit].rsplit("\n", 1)[0] + "\n…"
        print(self.L["inject"].format(path=status.as_posix()) + "\n\n" + body)
        if self.issues:
            print("\n" + self.L["h_inject"].format(n=self.issues, path=f"{self.L['system']}/{self.L['health']}.md"))


def slug(path):
    """Claude Code names a project's transcript folder after its path with every non-alphanumeric char as '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", help="project dir (default: $CLAUDE_PROJECT_DIR, hook cwd, or cwd)")
    ap.add_argument("--vault", help="override vault path from config")
    ap.add_argument("--home", help="override home dir (tests)")
    ap.add_argument("--transcripts", help="override transcripts dir")
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    ap.add_argument("--hook", action="store_true", help="read hook JSON from stdin")
    ap.add_argument("--inject", action="store_true", help="print the status board (SessionStart context)")
    a = ap.parse_args(argv)

    hook = {}
    if a.hook and not sys.stdin.isatty():
        try:
            hook = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            hook = {}
    project = pathlib.Path(a.project or os.environ.get("CLAUDE_PROJECT_DIR") or hook.get("cwd") or os.getcwd()).resolve()
    cfg_path = project / ".claude" / "showrunner.json"
    if not cfg_path.exists():
        return 0
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    vault = pathlib.Path(os.path.expanduser(a.vault or cfg.get("vault", "")))
    if not vault.is_absolute():
        vault = (project / vault).resolve()
    if not (a.vault or cfg.get("vault")) or not vault.is_dir():
        print(f"showrunner: vault not found: {vault}", file=sys.stderr)
        return 0
    home = pathlib.Path(a.home).resolve() if a.home else pathlib.Path.home()
    if a.transcripts:
        transcripts = pathlib.Path(a.transcripts)
    elif hook.get("transcript_path"):
        transcripts = pathlib.Path(hook["transcript_path"]).parent
    else:
        transcripts = home / ".claude" / "projects" / slug(project)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()

    s = Sync(project, vault, home, transcripts, cfg, today)
    s.run(project / ".claude" / ".showrunner-cache.json")
    if (a.inject or hook.get("hook_event_name") == "SessionStart") and cfg.get("inject_status", True):
        s.inject()
    return 0


if __name__ == "__main__":
    sys.exit(main())
