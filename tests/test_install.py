import shutil
import subprocess
import sys
import unittest
import zipfile

from helpers import HarnessCase, run, sh


class InstallTests(HarnessCase):
    def test_fresh_install_passes_check(self):
        code, out = self.cli("check")
        self.assertEqual(code, 0, out)

    def test_vendored_pyz_runs_without_package(self):
        pyz = self.repo / ".harness/sdlc.pyz"
        proc = subprocess.run([sys.executable, "-I", str(pyz), "--root", str(self.repo), "check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(any("template" in n for n in zipfile.ZipFile(pyz).namelist()))

    def test_skills_index_and_claude_adapter(self):
        self.assertIn("`sdlc-orchestrator`", (self.repo / "AGENTS.md").read_text())
        self.assertTrue((self.repo / ".claude/skills/sdlc-design/SKILL.md").exists())
        self.assertIn("@AGENTS.md", (self.repo / "CLAUDE.md").read_text())

    def test_stale_index_detected_and_fixed_by_sync(self):
        extra = self.repo / ".agents/skills/sdlc-extra"
        extra.mkdir()
        (extra / "SKILL.md").write_text("---\nname: sdlc-extra\ndescription: Extra skill for tests.\n---\nbody\n")
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

    def test_copy_mode_and_gitlab(self):
        target = self.repo.parent / "gl"
        target.mkdir()
        sh(target, "git", "init", "-q")
        code, out = run("init", str(target), "--mode", "copy", "--ci", "gitlab", "--agents", "claude-code")
        self.assertEqual(code, 0, out)
        self.assertTrue((target / ".gitlab-ci.sdlc.yml").exists())
        self.assertFalse((target / ".github/workflows").exists())
        self.assertIn('platform = "gitlab"', (target / ".harness/roster.toml").read_text())
        self.assertFalse((target / ".claude/skills").is_symlink())
        skill = target / ".agents/skills/sdlc-plan/SKILL.md"
        skill.write_text(skill.read_text() + "\nextra\n")
        code, out = run("--root", str(target), "check")
        self.assertEqual(code, 1)
        self.assertIn("drifted", out)
        shutil.rmtree(target)


class CommitMessageTests(HarnessCase):
    def test_conventional_commits(self):
        msg = self.repo / "msg"
        msg.write_text("updated stuff\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 1)
        msg.write_text("fix(auth)!: reject expired tokens\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 0)


class RegulatedTests(HarnessCase):
    profile = "regulated"

    def test_commit_trailer_required(self):
        msg = self.repo / "msg"
        msg.write_text("feat(api): add limit\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 1)
        msg.write_text("feat(api): add limit\n\nChange: 2026-09-16-rate-limit\n")
        self.assertEqual(self.cli("commit-msg", str(msg))[0], 0)

    def test_doctor_requires_codeowners_and_roster_members(self):
        code, out = self.cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("CODEOWNERS", out)
        self.assertIn("has no members", out)


if __name__ == "__main__":
    unittest.main()


class WorkflowHygieneTests(unittest.TestCase):
    """Shipped workflows must pass the harness's own sensors (found by the first real CI run, v0.5.1)."""

    def workflows(self):
        from helpers import ROOT
        return sorted((ROOT / "src/sdlc_harness/template/.github/workflows").glob("*.yml")) + \
            sorted((ROOT / ".github/workflows").glob("*.yml"))

    def test_actions_pinned_to_commit_sha(self):
        import re
        for f in self.workflows():
            for line in f.read_text().splitlines():
                if m := re.match(r"^\s*-?\s*uses:\s*(\S+)", line):
                    self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", f"{f.name}: {line.strip()}")

    def test_dependabot_configs_set_cooldown(self):
        from helpers import ROOT
        from sdlc_harness import yamlish
        for f in (ROOT / "src/sdlc_harness/template/.github/dependabot.yml", ROOT / ".github/dependabot.yml"):
            for update in yamlish.loads(f.read_text())["updates"]:
                self.assertGreaterEqual(update.get("cooldown", {}).get("default-days", 0), 1, f.name)

    def test_no_github_context_interpolated_in_run_steps(self):
        from sdlc_harness import yamlish
        for f in self.workflows():
            data = yamlish.loads(f.read_text())
            for job in (data.get("jobs") or {}).values():
                for step in job.get("steps", []):
                    self.assertNotIn("${{", step.get("run", ""), f"{f.name}: {step.get('name')}")
