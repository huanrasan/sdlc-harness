import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

import sdlc  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = sdlc.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            out.write(str(exc.code))
    return code, out.getvalue()


class HarnessTestCase(unittest.TestCase):
    profile = "standard"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        code, out = run("init", str(self.repo), "--profile", self.profile)
        self.assertEqual(code, 0, out)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cli(self, *argv: str) -> tuple[int, str]:
        return run("--root", str(self.repo), *argv)

    def change_dir(self) -> Path:
        return next(p for p in (self.repo / "docs/changes").iterdir() if p.is_dir())

    def fill(self, *names: str) -> None:
        for name in names:
            path = self.change_dir() / name
            path.write_text(path.read_text().replace(sdlc.PLACEHOLDER, "done"))


class TemplateTests(HarnessTestCase):
    def test_fresh_install_passes_check(self):
        code, out = self.cli("check")
        self.assertEqual(code, 0, out)

    def test_skills_index_generated(self):
        text = (self.repo / "AGENTS.md").read_text()
        for skill in ("sdlc-orchestrator", "sdlc-verify", "sdlc-maintain"):
            self.assertIn(f"`{skill}`", text)

    def test_claude_adapter_links_skills(self):
        link = self.repo / ".claude/skills"
        self.assertTrue(link.is_symlink())
        self.assertTrue((link / "sdlc-design/SKILL.md").exists())
        self.assertIn("@AGENTS.md", (self.repo / "CLAUDE.md").read_text())

    def test_stale_index_detected(self):
        (self.repo / ".agents/skills/sdlc-extra").mkdir()
        (self.repo / ".agents/skills/sdlc-extra/SKILL.md").write_text(
            "---\nname: sdlc-extra\ndescription: Extra skill for tests.\n---\nbody\n"
        )
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        self.assertIn("stale", out)
        self.assertEqual(self.cli("sync")[0], 0)
        self.assertEqual(self.cli("check")[0], 0)

    def test_invalid_skill_name_rejected(self):
        bad = self.repo / ".agents/skills/Bad--Name"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: Bad--Name\ndescription: x\n---\n")
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        self.assertIn("invalid name", out)


class GateTests(HarnessTestCase):
    def test_new_feature_creates_required_templates(self):
        self.cli("new", "feature", "rate-limit", "--risk", "high")
        files = {p.name for p in self.change_dir().iterdir()}
        self.assertTrue({"spec.md", "design.md", "threat-model.md", "plan.md", "runbook.md"} <= files)

    def test_phase_gate_blocks_unfilled_spec(self):
        self.cli("new", "feature", "rate-limit", "--risk", "medium")
        cid = self.change_dir().name
        code, out = self.cli("phase", cid, "design")
        self.assertEqual(code, 1)
        self.assertIn("gate blocked", out)
        self.assertIn('phase = "spec"', (self.change_dir() / "change.toml").read_text())

        self.fill("spec.md")
        code, out = self.cli("phase", cid, "design")
        self.assertEqual(code, 0, out)

    def test_cannot_skip_phases(self):
        self.cli("new", "fix", "typo-crash", "--risk", "low")
        code, out = self.cli("phase", self.change_dir().name, "implement")
        self.assertNotEqual(code, 0)
        self.assertIn("cannot skip", out)

    def test_architecture_requires_adr(self):
        self.cli("new", "architecture", "event-bus", "--risk", "low")
        self.fill("spec.md", "design.md")
        cid = self.change_dir().name
        self.assertEqual(self.cli("phase", cid, "design")[0], 0)
        code, out = self.cli("phase", cid, "plan")
        self.assertEqual(code, 1)
        self.assertIn("ADR", out)

    def test_ai_disclosure_required(self):
        self.cli("new", "fix", "npe", "--risk", "low")
        meta = self.change_dir() / "change.toml"
        meta.write_text(meta.read_text().replace("ai_assisted = true\n", ""))
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        self.assertIn("ai_assisted", out)


class RegulatedTests(HarnessTestCase):
    profile = "regulated"

    def test_commit_trailer_required(self):
        msg = self.repo / "msg"
        msg.write_text("feat(api): add limit\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 1)
        msg.write_text("feat(api): add limit\n\nChange: 2026-09-16-rate-limit\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 0)

    def test_doctor_requires_codeowners(self):
        code, out = self.cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("CODEOWNERS", out)


class CommitMessageTests(HarnessTestCase):
    def test_conventional_commits(self):
        msg = self.repo / "msg"
        msg.write_text("updated stuff\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 1)
        msg.write_text("fix(auth)!: reject expired tokens\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 0)


if __name__ == "__main__":
    unittest.main()
