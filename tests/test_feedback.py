"""Behaviour added after taking the harness through a full lifecycle on a real application (field feedback, v0.7).

Each test names the friction it removes, so the reason survives longer than the memory of the session that found it.
"""
import re
import unittest
from unittest import mock

from helpers import VALID, HarnessCase, sh
from sdlc_harness import gates, memory, tdd


class GlobSemanticsTests(unittest.TestCase):
    """`src/**/*.ts` used to miss `src/proxy.ts`, so source files were silently classified as 'other'."""

    def test_double_star_matches_zero_directories(self):
        cfg = {"tdd": {"source_globs": ["src/**/*.ts"], "test_globs": ["tests/**"]}}
        self.assertEqual(tdd.classify("src/proxy.ts", cfg), "source")
        self.assertEqual(tdd.classify("src/lib/deep/proxy.ts", cfg), "source")
        self.assertEqual(tdd.classify("tests/a/b.ts", cfg), "test")

    def test_single_star_stays_inside_one_segment(self):
        cfg = {"tdd": {"source_globs": ["src/*.ts"]}}
        self.assertEqual(tdd.classify("src/proxy.ts", cfg), "source")
        self.assertEqual(tdd.classify("src/lib/proxy.ts", cfg), "other")


class TddExplainTests(HarnessCase):
    def test_explain_lists_classification_and_warns_about_ignored_source(self):
        (self.repo / "src").mkdir()
        (self.repo / "src/proxy.ts").write_text("export const a = 1\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests/proxy.test.ts").write_text("test('x', () => {})\n")
        cfg = self.repo / "harness.toml"
        cfg.write_text(cfg.read_text().replace("source_globs = []", 'source_globs = ["src/*.js"]'))
        sh(self.repo, "git", "add", "-A")
        code, out = self.cli("tdd", "--explain")
        self.assertEqual(code, 0, out)
        self.assertIn("src/proxy.ts", out)
        self.assertIn("test-first sensor ignores them", out)

    def test_base_is_required_without_explain(self):
        code, out = self.cli("tdd")
        self.assertEqual(code, 2)
        self.assertIn("--base", out)


class CostGateTests(HarnessCase):
    COST = """# Cost
| Component | Monthly (USD) | Driver |
|---|---|---|
| database | 40 | storage |

Total monthly (production): {total}

## Assumptions
Steady traffic.

## Guardrails
{guardrails}
"""
    GUARDRAILS = ("Monthly budget of USD 100 with alerts at 80% and 100%.\n"
                  "Cost allocation tags: env, service, owner.\n"
                  "Idle policy: preview environments scale to zero overnight.\n")

    def cost_report(self, total: str, guardrails: str = GUARDRAILS) -> str:
        text = self.COST.format(total=total, guardrails=guardrails)
        ctx = gates.Context(self.repo, self.repo, {}, {})
        return "\n".join(gates.check_cost(text, "cost.md", ctx).errors)

    def test_currency_may_precede_the_amount(self):
        """'Total monthly (production): USD 77,40' used to fail while '77,40 USD' passed."""
        self.assertNotIn("needs an amount", self.cost_report("USD 77,40"))
        self.assertNotIn("needs an amount", self.cost_report("77,40 USD"))
        self.assertNotIn("needs an amount", self.cost_report("$77.40"))
        self.assertIn("needs an amount", self.cost_report("to be confirmed"))

    def test_guardrails_are_judged_by_content_not_punctuation(self):
        """A prose line ending in ':' used to fail the section, and the message never said why."""
        prose = self.GUARDRAILS + "Reviewed every quarter by the owners listed above:\n"
        self.assertEqual(self.cost_report("USD 40", prose), "")
        out = self.cost_report("USD 40", "Monthly budget of USD 100.\n")
        self.assertIn("alert thresholds", out)
        self.assertIn("allocation tags", out)
        self.assertIn("an idle policy", out)


class BlockedCriterionTests(HarnessCase):
    SPEC_AC = ("# Spec\n## Acceptance criteria\n| ID | Given / When / Then | Verified by |\n|---|---|---|\n"
               "| AC-1 | Given x, when y, then z | test_z |\n")

    def verification(self, result: str, evidence: str) -> str:
        (self.repo / "spec.md").write_text(self.SPEC_AC)
        text = ("# Verification\n## Acceptance criteria\n| ID | Result | Evidence |\n|---|---|---|\n"
                f"| AC-1 | {result} | {evidence} |\n")
        ctx = gates.Context(self.repo, self.repo, {}, {})
        return "\n".join(gates.check_verification(text, "verification.md", ctx).errors)

    def test_blocked_needs_an_owner_and_a_reason(self):
        self.assertIn("must name an owner and a reason", self.verification("blocked", "cannot do it"))

    def test_blocked_with_an_owner_is_recorded_but_still_blocks(self):
        out = self.verification("blocked", "blocked - owner: rita - needs repository admin to protect the branch")
        self.assertIn("AC-1 is blocked (owner: rita)", out)
        self.assertIn("verify cannot close", out)

    def test_an_unknown_result_names_the_open_states(self):
        self.assertIn("blocked/pending with an owner", self.verification("pendiente", "soon"))

    def test_a_passing_result_is_unaffected(self):
        self.assertEqual(self.verification("pass", "`test_z`"), "")


class AmendTests(HarnessCase):
    def setUp(self) -> None:
        super().setUp()
        self.set_roster(product_owner=["alice"])
        self.cid = self.new_change(change_type="fix", risk="low")  # standard: starts at spec, needs an approval
        self.write_valid("spec.md")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "feat: spec")
        self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.advance(self.cid, "design")

    def test_amend_shows_the_diff_and_re_approves(self):
        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nPublished digest: sha256:abc\n")
        self.assertIn("is stale (content changed)", self.cli("check", "--change", self.cid)[1])
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("builtins.input", return_value="yes"):
            code, out = self.cli("amend", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 0, out)
        self.assertIn("+Published digest: sha256:abc", out)
        self.assertEqual(self.cli("check", "--change", self.cid)[0], 0)
        self.assertIn("amend-reviewed", (self.change_dir() / "audit.jsonl").read_text())

    def test_an_agent_cannot_amend(self):
        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nedited\n")
        with mock.patch("sys.stdin.isatty", return_value=False):
            code, out = self.cli("amend", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 2)
        self.assertIn("human at a terminal", out)
        self.assertIn("is stale (content changed)", self.cli("check", "--change", self.cid)[1])

    def test_refusing_the_diff_leaves_the_receipt_stale(self):
        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nedited\n")
        with mock.patch("sys.stdin.isatty", return_value=True), mock.patch("builtins.input", return_value="no"):
            code, out = self.cli("amend", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 1)
        self.assertIn("not amended", out)
        self.assertIn("is stale (content changed)", self.cli("check", "--change", self.cid)[1])

    def test_unchanged_artifact_needs_no_amendment(self):
        with mock.patch("sys.stdin.isatty", return_value=True):
            code, out = self.cli("amend", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 0)
        self.assertIn("nothing to amend", out)


class ProposalTests(HarnessCase):
    def test_proposed_deviation_is_pending_until_a_human_approves(self):
        self.set_roster(architect=["ana"])
        code, out = self.cli("deviation", "propose", "sensors.test_first",
                             "--reason", "legacy module, ISSUE-42 adds tests", "--days", "30")
        self.assertEqual(code, 0, out)
        text = (self.repo / ".harness/deviations.toml").read_text()
        self.assertIn('approver = ""', text)
        self.assertIn("is proposed and awaits approval", self.cli("check")[1])

        code, out = self.cli("deviation", "approve", "sensors.test_first", "--as", "ana", "--role", "architect")
        self.assertEqual(code, 0, out)
        text = (self.repo / ".harness/deviations.toml").read_text()
        self.assertIn('approver = "ana"', text)
        self.assertIn('role = "architect"', text)
        self.assertNotIn("awaits approval", self.cli("check")[1])

    def test_an_unauthorized_role_cannot_approve(self):
        self.set_roster(product_owner=["pat"])
        self.cli("exception", "propose", "semgrep.eval-detected", "tools/*.py", "--reason", "fixed allowlist")
        code, out = self.cli("exception", "approve", "semgrep.eval-detected", "tools/*.py",
                             "--as", "pat", "--role", "product-owner")
        self.assertEqual(code, 2)
        self.assertIn("may not approve", out)

    def test_a_proposal_expires_and_states_its_reason(self):
        code, out = self.cli("deviation", "propose", "sensors.contracts", "--reason", "x", "--expires", "2099-01-01")
        self.assertEqual(code, 0, out)
        self.assertIn("expires = 2099-01-01", (self.repo / ".harness/deviations.toml").read_text())
        code, out = self.cli("deviation", "propose", "sensors.contracts", "--reason", "x")
        self.assertEqual(code, 2)
        self.assertIn("already pending", out)

    def test_a_reason_is_required(self):
        code, out = self.cli("deviation", "propose", "sensors.test_first")
        self.assertEqual(code, 2)
        self.assertIn("--reason is required", out)


class StagedCheckTests(HarnessCase):
    def test_staged_only_validates_the_change_the_commit_touches(self):
        first = self.new_change(slug="one")
        code, out = self.cli("new", "feature", "two", "--risk", "medium")
        self.assertEqual(code, 0, out)
        second = next(p.name for p in (self.repo / "docs/changes").iterdir() if p.name.endswith("two"))
        sh(self.repo, "git", "add", f"docs/changes/{first}")
        code, out = self.cli("check", "--staged")
        self.assertNotIn(second, out)

    def test_a_gitkeep_is_not_mistaken_for_a_change(self):
        (self.repo / "docs/changes/.gitkeep").touch()
        sh(self.repo, "git", "add", "-A")
        code, out = self.cli("check", "--staged")
        self.assertNotIn("change not found", out)


class MemorySlugTests(unittest.TestCase):
    def test_slug_is_ascii_and_cut_on_a_word_boundary(self):
        slug = memory._slug("Better Auth no exige 2FA en inicios de sesión por enlace mágico")
        self.assertTrue(slug.isascii(), slug)
        self.assertFalse(slug.endswith("-"))
        self.assertLessEqual(len(slug), 60)
        self.assertNotIn("mag", slug.rsplit("-", 1)[-1])  # no word cut in half
        self.assertEqual(memory._slug("   "), "entry")
        self.assertEqual(len(memory._slug("x" * 200)), 60)


class ApprovalMessageTests(HarnessCase):
    def test_the_gate_spells_out_the_command_a_human_must_run(self):
        self.set_roster(product_owner=["alice"])
        cid = self.new_change(change_type="fix", risk="low")
        self.write_valid("spec.md")
        out = self.cli("phase", cid, "design")[1]
        self.assertRegex(out, rf"approve {re.escape(cid)} spec\.md --as <username> --role product-owner")


class ReleaseConfigTests(HarnessCase):
    def test_config_reads_a_dotted_key_with_a_default(self):
        code, out = self.cli("config", "release.sbom_source")
        self.assertEqual((code, out.strip()), (0, "dir:dist"))
        code, out = self.cli("config", "release.nothing", "--default", "dir:dist")
        self.assertEqual(out.strip(), "dir:dist")

    def test_the_release_workflow_uses_the_configured_source(self):
        workflow = (self.repo / ".github/workflows/sdlc-release.yml").read_text()
        self.assertIn("config release.sbom_source", workflow)
        self.assertNotIn("syft:v1.52.0@sha256:500e2d872ac019436926e8322b4fc1f39441d94d21f6f4046c6ff29b30e8cb02 dir:dist",
                         workflow)


if __name__ == "__main__":
    unittest.main()
