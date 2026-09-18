import json
import subprocess
import sys
import unittest
from pathlib import Path as P
import zipfile
from pathlib import Path

from helpers import ROOT, HarnessCase, run, sh

from sdlc_harness import installer


class UpgradeTests(HarnessCase):
    def manifest(self):
        return (self.repo / ".harness/manifest.toml").read_text()

    def simulate_old_version(self, rel, old_content):
        """Pretend `rel` was installed from an older template with `old_content`."""
        path = self.repo / rel
        path.write_text(old_content)
        text = self.manifest()
        import re
        digest = installer._digest(old_content.encode(), rel)
        text = re.sub(rf'^"{re.escape(rel)}" = ".*"$', f'"{rel}" = "{digest}"', text, flags=re.M)
        (self.repo / ".harness/manifest.toml").write_text(text)

    def test_noop_upgrade_after_init(self):
        code, out = self.cli("upgrade")
        self.assertEqual(code, 0, out)
        self.assertNotIn("updated:", out)
        self.assertNotIn("sdlc-new", out)
        self.assertEqual(self.cli("check")[0], 0)

    def test_unmodified_file_is_updated_and_customized_file_gets_sdlc_new(self):
        skill = ".agents/skills/sdlc-plan/SKILL.md"
        template = (self.repo / skill).read_text()
        self.simulate_old_version(skill, template.replace("# Plan", "# Plan (old)"))
        spec_tpl = "docs/sdlc/templates/spec.md"
        self.simulate_old_version(spec_tpl, "old template\n")
        (self.repo / spec_tpl).write_text("old template\ncustomized by the team\n")
        code, out = self.cli("upgrade", "--dry-run")
        self.assertIn(f"updated: {skill}", out)
        self.assertIn("(old)", (self.repo / skill).read_text())
        code, out = self.cli("upgrade")
        self.assertEqual((self.repo / skill).read_text(), template)
        self.assertIn("customized by the team", (self.repo / spec_tpl).read_text())
        self.assertTrue((self.repo / (spec_tpl + ".sdlc-new")).exists())
        self.assertIn("customized: docs/sdlc/templates/spec.md", out)

    def test_agents_md_index_and_project_fill_handling(self):
        agents = self.repo / "AGENTS.md"
        agents.write_text(agents.read_text().replace("- Build: `<!-- sdlc:fill -->`", "- Build: `make`"))
        code, out = self.cli("upgrade")
        self.assertIn("- Build: `make`", agents.read_text())
        self.assertFalse((self.repo / "AGENTS.md.sdlc-new").exists())  # template unchanged: keep customization

    def test_toml_merge_adds_missing_tables_and_keys_without_changing_values(self):
        cfg = self.repo / "harness.toml"
        text = cfg.read_text().replace('profile = "standard"', 'profile = "regulated"')
        text = text.split("\n[evidence]")[0] + "\n"  # drop a whole table
        cfg.write_text(text)
        roster = self.repo / ".harness/roster.toml"
        roster.write_text(roster.read_text().replace('"outcome.md" = ["product-owner"]\n', "")
                          .replace('[roles.finops]\nmembers = []\n', ""))
        code, out = self.cli("upgrade")
        self.assertEqual(code, 0, out)
        merged = cfg.read_text()
        self.assertIn('profile = "regulated"', merged)
        self.assertIn("[evidence]", merged)
        self.assertIn('"outcome.md" = ["product-owner"]', roster.read_text())
        self.assertIn("[roles.finops]", roster.read_text())
        self.assertEqual(self.cli("check")[0], 0)

    def test_obsolete_unmodified_files_removed_and_legacy_cli_replaced(self):
        obsolete = self.repo / "docs/sdlc/templates/old.md"
        obsolete.write_text("old\n")
        text = self.manifest() + f'"docs/sdlc/templates/old.md" = "{installer._digest(b"old" + bytes([10]))}"\n'
        (self.repo / ".harness/manifest.toml").write_text(text)
        (self.repo / ".harness/sdlc.py").write_text("legacy")
        code, out = self.cli("upgrade")
        self.assertFalse(obsolete.exists())
        self.assertFalse((self.repo / ".harness/sdlc.py").exists())
        self.assertIn("removed legacy", out)


class BundleTests(HarnessCase):
    def test_full_bundle_is_deterministic_and_can_init_without_package(self):
        a, b = self.repo.parent / "a.pyz", self.repo.parent / "b.pyz"
        installer.build_pyz(a, full=True)
        installer.build_pyz(b, full=True)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        self.assertTrue(any(n.startswith("sdlc_harness/template/") for n in zipfile.ZipFile(a).namelist()))
        target = self.repo.parent / "fresh"
        target.mkdir()
        sh(target, "git", "init", "-q")
        proc = subprocess.run([sys.executable, "-I", str(a), "init", str(target), "--profile", "lite"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc = subprocess.run([sys.executable, "-I", str(target / ".harness/sdlc.pyz"), "--root", str(target), "check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc = subprocess.run([sys.executable, "-I", str(a), "--root", str(target), "upgrade"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class AdoptTests(unittest.TestCase):
    def test_brownfield_detection_and_adoption(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sh(repo, "git", "init", "-q")
            files = {
                "package.json": json.dumps({"scripts": {"build": "tsc", "test": "vitest run", "lint": "eslint ."}}),
                "pnpm-lock.yaml": "",
                "src/app.tsx": "export const App = () => null\n",
                "src/app.test.ts": "test('x', () => {})\n",
                "api/openapi.yaml": "openapi: 3.0.3\ninfo: {title: x, version: 1.0.0}\npaths: {}\n",
                "infra/main.tf": 'resource "null_resource" "x" {}\n',
                "migrations/001_init.sql": "create table t(id int);\n",
                ".gitlab-ci.yml": "stages: [test]\n",
                "AGENTS.md": "# Team rules\n\nUse conventional commits.\n",
            }
            for path, content in files.items():
                (repo / path).parent.mkdir(parents=True, exist_ok=True)
                (repo / path).write_text(content)
            code, out = run("init", str(repo), "--adopt", "--profile", "lite")
            self.assertEqual(code, 0, out)
            self.assertTrue((repo / ".gitlab-ci.sdlc.yml").exists())  # CI auto-detected
            agents = (repo / "AGENTS.md").read_text()
            self.assertIn("# Team rules", agents)
            self.assertIn("## How work flows here (SDLC harness)", agents)
            self.assertIn("`sdlc-orchestrator`", agents)
            self.assertIn('files = ["api/openapi.yaml"]', (repo / "harness.toml").read_text())
            report = (repo / "docs/sdlc/adoption.md").read_text()
            for fragment in ("TypeScript", "pnpm build", "pnpm test", "Terraform/OpenTofu", "api/openapi.yaml",
                             "GitLab CI", "ui, api, data, infra"):
                self.assertIn(fragment, report)


class ExistingAgentFilesTests(unittest.TestCase):
    def test_symlinked_claude_md_and_existing_skills_directory(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sh(repo, "git", "init", "-q")
            (repo / "AGENTS.md").write_text("# Rules\n")
            os.symlink("AGENTS.md", repo / "CLAUDE.md")
            own = repo / ".claude/skills/team-skill"
            own.mkdir(parents=True)
            (own / "SKILL.md").write_text("---\nname: team-skill\ndescription: Team skill.\n---\n")
            code, out = run("init", str(repo), "--adopt", "--agents", "claude-code")
            self.assertEqual(code, 0, out)
            self.assertTrue((repo / ".claude/skills/team-skill/SKILL.md").exists())
            self.assertTrue((repo / ".claude/skills/sdlc-plan").is_symlink())
            code, out = run("--root", str(repo), "check")
            self.assertEqual(code, 0, out)


class BaselineTests(HarnessCase):
    def test_baseline_creates_exceptions_awaiting_approver(self):
        ev = self.repo / "sdlc-evidence"
        ev.mkdir()
        (ev / "sast.sarif").write_text(json.dumps({"runs": [{"tool": {"driver": {"name": "s"}}, "results": [
            {"ruleId": "py.eval", "level": "error",
             "locations": [{"physicalLocation": {"artifactLocation": {"uri": "legacy/x.py"}}}]}]}]}))
        code, out = self.cli("evidence", "baseline")
        self.assertIn("1 exception(s) added", out)
        self.assertIn("baseline: no new findings", self.cli("evidence", "baseline")[1])
        code, out = self.cli("evidence", "check", "--require", "")
        self.assertEqual(code, 1)
        self.assertIn("awaits a human approver", out)


class VendoredCliLimitsTests(unittest.TestCase):
    """The vendored `.harness/sdlc.pyz` has no templates; commands that need them must say so, not crash.

    Found while validating a real repository after an upgrade: `sdlc upgrade` from the vendored CLI ended in a
    ValueError traceback from zipfile.
    """

    def test_upgrade_from_the_vendored_cli_explains_itself(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path as P

        from helpers import run, sh
        with tempfile.TemporaryDirectory() as tmp:
            repo = P(tmp) / "repo"
            repo.mkdir()
            sh(repo, "git", "init", "-q")
            self.assertEqual(run("init", str(repo), "--profile", "lite")[0], 0)
            proc = subprocess.run([sys.executable, str(repo / ".harness/sdlc.pyz"), "upgrade", "--dry-run"],
                                  cwd=repo, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
            output = proc.stdout + proc.stderr
            self.assertNotIn("Traceback", output)
            self.assertIn("ships without templates", output)
            self.assertIn("sdlc-full.pyz", output)


class DistributionTests(unittest.TestCase):
    def test_generated_packages_are_in_sync(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/build_distribution.py"), "--check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        from sdlc_harness import __version__
        self.assertEqual(plugin["version"], __version__)


class EvalGraderTests(unittest.TestCase):
    def test_simulated_agents_separate_good_from_bad(self):
        import tempfile
        with tempfile.TemporaryDirectory() as out:
            for agent, expected in (("simulated-good", 0), ("simulated-bad", 1)):
                proc = subprocess.run([sys.executable, str(ROOT / "evals/run.py"), "--agent", agent, "--output", out],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
                self.assertIn("100%" if expected == 0 else "| 0% (0/7) |", proc.stdout)

    def test_an_agent_that_never_ran_is_not_counted_as_a_behavioural_failure(self):
        """A usage limit or an expired session must not read as the agent breaking the harness."""
        import tempfile
        with tempfile.TemporaryDirectory() as out:
            agents = P(out) / "agents.toml"
            agents.write_text('[agents.broken]\ncommand = ["sh", "-c", "echo \'session limit reached\' >&2; exit 1"]\n'
                              "timeout = 30\n")
            proc = subprocess.run([sys.executable, str(ROOT / "evals/run.py"), "--agent", "broken",
                                   "--agents-file", str(agents), "--scenario", "trivial-no-ceremony",
                                   "--output", out], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("ERROR", proc.stdout)
            self.assertIn("could not be measured", proc.stdout)
            self.assertIn("n/a", proc.stdout)


if __name__ == "__main__":
    unittest.main()
