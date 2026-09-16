import unittest

from helpers import ADR, VALID, HarnessCase

from sdlc_harness.core import section, tables


class ParsingTests(unittest.TestCase):
    def test_section_prefers_exact_heading(self):
        text = "## Decision drivers\nA\n## Decision\nB\n"
        self.assertEqual(section(text, "Decision"), "B")
        self.assertEqual(section(text, "Decision dr"), "A")

    def test_tables(self):
        rows = tables("| ID | Result |\n|---|---|\n| AC-1 | pass |\n")[0]
        self.assertEqual(rows, [{"id": "AC-1", "result": "pass"}])


class PhaseTests(HarnessCase):
    """lite-like flow on standard without approvals: use low-risk fix (spec + verification only)."""

    def test_new_feature_creates_required_templates(self):
        self.new_change(risk="high")
        files = {p.name for p in self.change_dir().iterdir()}
        self.assertTrue({"spec.md", "design.md", "threat-model.md", "plan.md", "runbook.md", "audit.jsonl"} <= files)

    def test_placeholder_blocks_phase_and_keeps_state(self):
        cid = self.new_change(change_type="fix", risk="low")
        code, out = self.cli("phase", cid, "design")
        self.assertEqual(code, 1)
        self.assertIn("gate blocked", out)
        self.assertIn('phase = "spec"', (self.change_dir() / "change.toml").read_text())

    def test_cannot_skip_phases(self):
        cid = self.new_change(change_type="fix", risk="low")
        code, out = self.cli("phase", cid, "implement")
        self.assertNotEqual(code, 0)
        self.assertIn("cannot skip", out)

    def test_ai_disclosure_required(self):
        self.new_change(change_type="fix", risk="low")
        meta = self.change_dir() / "change.toml"
        meta.write_text(meta.read_text().replace("ai_assisted = true\n", ""))
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        self.assertIn("ai_assisted", out)


class SemanticGateTests(HarnessCase):
    profile = "lite"  # no approvals, so failures come only from semantic checks

    def setUp(self):
        super().setUp()
        self.profile_path = self.repo / ".harness/profiles/lite.toml"
        # Make every artifact mandatory without approvals to exercise all checkers.
        rules = "".join(
            f'\n[[rules]]\nartifact = "{a}"\nphase = "{p}"\ntypes = ["feature"]\nmin_risk = "low"\n'
            for a, p in [("spec.md", "spec"), ("design.md", "design"), ("threat-model.md", "design"),
                         ("plan.md", "plan"), ("verification.md", "verify"), ("review.md", "review"),
                         ("release.md", "release"), ("runbook.md", "release")])
        self.profile_path.write_text(rules)
        self.cid = self.new_change()
        self.write_valid(*VALID)

    def gate(self, phase="done"):
        meta = self.change_dir() / "change.toml"
        meta.write_text(meta.read_text().replace('phase = "spec"', f'phase = "{phase}"'))
        return self.cli("check", "--change", self.cid)

    def test_valid_change_passes_all_gates(self):
        code, out = self.gate()
        self.assertEqual(code, 0, out)

    def test_spec_needs_acceptance_criteria(self):
        (self.change_dir() / "spec.md").write_text("# Spec\n## Problem\nx\n")
        code, out = self.gate()
        self.assertIn("at least one acceptance criterion", out)
        self.assertIn("AC", out)

    def test_plan_must_trace_every_criterion_and_threat(self):
        spec = self.change_dir() / "spec.md"
        spec.write_text(spec.read_text().replace(
            "| AC-1 |", "| AC-2 | Given x, when y, then z | test |\n| AC-1 |"))
        code, out = self.gate()
        self.assertEqual(code, 1)
        self.assertIn("AC-2 from spec.md is missing in the traceability table", out)
        self.assertIn("AC-2 from spec.md has no verification result", out)

    def test_threat_without_control(self):
        tm = self.change_dir() / "threat-model.md"
        tm.write_text(tm.read_text().replace("| T-1 | retry queue |", "| T-2 | api | Spoofing | x | l | h |\n| T-1 | retry queue |"))
        code, out = self.gate()
        self.assertIn("T-2 has no control", out)
        self.assertIn("T-2 from threat-model.md is missing", out)

    def test_failed_verification_blocks(self):
        v = self.change_dir() / "verification.md"
        v.write_text(v.read_text().replace("| pass |", "| fail |"))
        code, out = self.gate()
        self.assertIn("AC-1 result is 'fail'", out)

    def test_cited_test_must_exist_when_test_paths_configured(self):
        cfg = self.repo / "harness.toml"
        cfg.write_text(cfg.read_text().replace("test_paths = []", 'test_paths = ["tests/**/*.py"]'))
        (self.repo / "tests").mkdir()
        (self.repo / "tests/test_pay.py").write_text("def test_other():\n    pass\n")
        code, out = self.gate()
        self.assertIn("cites test `test_retry` not found", out)
        (self.repo / "tests/test_pay.py").write_text("def test_retry():\n    pass\n")
        code, out = self.gate()
        self.assertEqual(code, 0, out)

    def test_review_verdict_and_fresh_context(self):
        r = self.change_dir() / "review.md"
        r.write_text(VALID["review.md"].replace("ready-for-human-approval", "changes-requested")
                     .replace(": yes", ": no").replace("[x]", "[ ]"))
        code, out = self.gate()
        self.assertIn("verdict is changes-requested", out)
        self.assertIn("fresh context", out)
        self.assertIn("unchecked items", out)

    def test_release_needs_rollback(self):
        (self.change_dir() / "release.md").write_text(VALID["release.md"].replace("Flag off.", ""))
        code, out = self.gate()
        self.assertIn("section 'Rollback' is empty", out)

    def test_semantic_checks_only_after_phase(self):
        (self.change_dir() / "release.md").write_text("# Release\n")
        code, out = self.gate(phase="verify")
        self.assertNotIn("release.md", out)


class AdrGateTests(HarnessCase):
    profile = "lite"

    def test_architecture_change_needs_valid_adr(self):
        cid = self.new_change(change_type="architecture", risk="low", slug="bus")
        self.write_valid("spec.md", "design.md")
        self.advance(cid, "design")
        code, out = self.cli("phase", cid, "plan")
        self.assertIn("requires at least one ADR", out)
        adr = self.repo / "docs/adr/0001-retry-library.md"
        adr.write_text(ADR.replace("2. Custom\n", ""))
        meta = self.change_dir() / "change.toml"
        meta.write_text(meta.read_text().replace("adrs = []", 'adrs = ["docs/adr/0001-retry-library.md"]'))
        code, out = self.cli("phase", cid, "plan")
        self.assertIn("at least two numbered options", out)
        adr.write_text(ADR)
        self.advance(cid, "plan")


if __name__ == "__main__":
    unittest.main()
