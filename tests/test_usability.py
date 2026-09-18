import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import VALID, ROOT, HarnessCase, run, sh

EXAMPLE = ROOT / "docs/examples/2026-09-17-staff-csv-export"


class StatusTests(HarnessCase):
    def test_empty_repository_suggests_the_first_command(self):
        code, out = self.cli("status")
        self.assertEqual(code, 0, out)
        self.assertIn("No change records yet", out)
        self.assertIn("sdlc.pyz new", out)

    def test_status_names_the_blocker_then_the_approver_then_the_phase_command(self):
        self.set_roster(product_owner=["alice"])
        cid = self.new_change(risk="low")  # standard: spec needs approval
        code, out = self.cli("status")
        self.assertEqual(code, 1)
        self.assertIn("unfilled sections", out)

        self.write_valid("spec.md")
        code, out = self.cli("status")
        self.assertIn("approval not approved", out)
        self.assertIn("by product-owner/tech-lead (alice)", out)
        self.assertIn("--role product-owner", out)

        self.cli("approve", cid, "spec.md", "--as", "alice", "--role", "product-owner")
        code, out = self.cli("status")
        self.assertEqual(code, 0, out)
        self.assertIn(f"next: python3 .harness/sdlc.pyz phase {cid} design", out)

        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nedited\n")
        code, out = self.cli("status")
        self.assertEqual(code, 1)
        self.assertIn("STALE", out)

    def test_json_output(self):
        self.new_change(change_type="fix", risk="low")
        code, out = self.cli("status", "--format", "json")
        data = json.loads(out)
        self.assertEqual(data["profile"], "standard")
        self.assertEqual(data["changes"][0]["phase"], "spec")
        self.assertIn("next_command", data["changes"][0])


class ExplainTests(HarnessCase):
    def test_phases_artifacts_roles_and_concepts(self):
        self.set_roster(security=["sam"])
        for topic, expected in [
            ("design", "next: plan"),
            ("spec.md", "approval receipt required: yes"),
            ("threat-model.md", "approving roles: security (sam)"),
            ("security", "may approve: threat-model.md"),
            ("receipt", "SHA-256 of the approved artifact"),
            ("ai", "adds ai-risk.md"),
        ]:
            code, out = self.cli("explain", topic)
            self.assertEqual(code, 0, out)
            self.assertIn(expected, out)

    def test_gate_messages_are_explained(self):
        for message, expected in [
            ("docs/changes/x/spec.md: requires approval by one of roles ['product-owner']", "A human gate is pending"),
            ("weakened test: added python skip/xfail in tests/test_a.py", "Test-Waiver"),
            ("cannot skip phases: spec -> implement", "one at a time"),
        ]:
            code, out = self.cli("explain", message)
            self.assertEqual(code, 0, out)
            self.assertIn(expected, out)

    def test_topic_list_and_unknown_topic(self):
        code, out = self.cli("explain")
        self.assertEqual(code, 0)
        self.assertIn("phases:", out)
        code, out = self.cli("explain", "quantum tunnelling")
        self.assertEqual(code, 1)
        self.assertIn("No topic matches", out)

    def test_works_outside_an_installed_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("--root", tmp, "explain", "spec")
            self.assertEqual(code, 0, out)
            self.assertIn("phase 'spec'", out)


class InteractiveInitTests(unittest.TestCase):
    def test_guided_setup_applies_answers(self):
        answers = ["lite", "claude-code,codex", "none", "symlink", "no",
                   "pat", "tomas", "", "sam", "", "", "", "", "", "", "no"]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            sh(repo, "git", "init", "-q")
            with mock.patch("builtins.input", side_effect=answers):
                code, out = run("init", str(repo), "--interactive")
            self.assertEqual(code, 0, out)
            self.assertIn('profile = "lite"', (repo / "harness.toml").read_text())
            roster = (repo / ".harness/roster.toml").read_text()
            self.assertIn('[roles.product-owner]\nmembers = ["pat"]', roster)
            self.assertIn('[roles.security]\nmembers = ["sam"]', roster)
            self.assertIn("separation_of_duties = false", roster)
            self.assertFalse((repo / ".github/workflows").exists())  # ci = none
            self.assertEqual(run("--root", str(repo), "check")[0], 0)

    def test_missing_input_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            sh(repo, "git", "init", "-q")
            with mock.patch("builtins.input", side_effect=EOFError):
                code, out = run("init", str(repo), "--interactive")
            self.assertEqual(code, 0, out)
            self.assertIn('profile = "standard"', (repo / "harness.toml").read_text())


class ExampleChangeRecordTests(HarnessCase):
    """The documented example must keep passing the gates it claims to pass."""

    def test_example_passes_every_gate(self):
        self.set_roster(product_owner=["pat"], tech_lead=["tomas"], architect=["ana"], security=["sam"],
                        release_manager=["rita"], ux_lead=["ulla"], data_steward=["dana"], sre=["seb"])
        target = self.repo / "docs/changes" / EXAMPLE.name
        shutil.copytree(EXAMPLE, target)
        code, out = self.cli("check", "--change", EXAMPLE.name)
        self.assertEqual(code, 0, out)
        code, out = self.cli("report", "trace", "--change", EXAMPLE.name, "--format", "json")
        self.assertEqual(json.loads(out)["gaps"], [], "the example must have no traceability gaps")

    def test_example_documentation_lists_every_artifact(self):
        readme = (ROOT / "docs/examples/README.md").read_text()
        for f in sorted(EXAMPLE.iterdir()):
            self.assertIn(f.name, readme, f"{f.name} is not described in docs/examples/README.md")


class DemoAndSiteTests(unittest.TestCase):
    def test_demo_recording_is_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/record_demo.py"), "--check"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_site_navigation_points_at_existing_files(self):
        import re
        text = (ROOT / "mkdocs.yml").read_text()
        for target in re.findall(r":\s*([\w./-]+\.md)\s*$", text, re.M):
            self.assertTrue((ROOT / "docs" / target).exists(), target)


if __name__ == "__main__":
    unittest.main()
