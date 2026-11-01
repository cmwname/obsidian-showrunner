"""Rebuild examples/: the fictional studio (examples/demo) and its vault (examples/demo-vault).

Hand-written demo notes in examples/demo-vault are kept; only System/ is regenerated.
Run: python tools/build_demo.py
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

import fixture  # noqa: E402
import sync  # noqa: E402

demo = ROOT / "examples" / "demo"
vault = ROOT / "examples" / "demo-vault"
shutil.rmtree(demo, ignore_errors=True)
project, home, tr = fixture.build(demo)
# The fixture points at ../vault; the published demo vault sits next to demo/.
(project / ".claude" / "showrunner.json").write_text(
    (project / ".claude" / "showrunner.json").read_text(encoding="utf-8").replace('"../vault"', '"../../demo-vault"'),
    encoding="utf-8")
for f in (ROOT / "templates" / "vault").rglob("*"):
    target = vault / f.relative_to(ROOT / "templates" / "vault")
    if f.is_file() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
sync.main(["--project", str(project), "--home", str(home), "--transcripts", str(tr), "--today", "2026-11-05"])
(project / ".claude" / ".showrunner-cache.json").unlink(missing_ok=True)
print(f"demo vault: {vault}")
