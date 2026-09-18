import json
import unittest

from helpers import VALID, HarnessCase, sh

from sdlc_harness import platform


class FakeClient:
    def __init__(self, approvals, pr_author="dev", authors=None, teams=None, signatures=None):
        self._approvals, self._author = approvals, pr_author
        self._authors, self._teams = authors or {}, teams or {}
        self._signatures = signatures or {}

    def signature(self, sha):
        return self._signatures.get(sha, (False, ""))

    def approvals(self):
        return self._approvals

    def pr_author(self):
        return self._author

    def commit_authors(self):
        return self._authors

    def in_team(self, team, user):
        return user in self._teams.get(team, [])


class ReceiptTests(HarnessCase):
    def setUp(self):
        super().setUp()
        self.set_roster(product_owner=["alice"], tech_lead=["tina"])
        self.cid = self.new_change(risk="low")  # standard: spec approval required
        self.write_valid("spec.md")
        self.spec = f"docs/changes/{self.cid}/spec.md"

    def test_gate_requires_approval(self):
        code, out = self.cli("phase", self.cid, "design")
        self.assertEqual(code, 1)
        self.assertIn("requires approval by one of roles ['product-owner', 'tech-lead']", out)

    def test_approval_unblocks_and_edit_invalidates(self):
        code, out = self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 0, out)
        self.advance(self.cid, "design")
        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nOne more line.\n")
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        self.assertIn("approval by alice is stale", out)

    def test_non_member_and_unauthorized_role_rejected(self):
        code, out = self.cli("approve", self.cid, "spec.md", "--as", "mallory", "--role", "product-owner")
        self.assertEqual(code, 2)
        self.assertIn("not a member", out)
        code, out = self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "security")
        self.assertEqual(code, 2)
        self.assertIn("not authorized", out)

    def test_cannot_approve_placeholder_content(self):
        (self.change_dir() / "spec.md").write_text("<!-- sdlc:fill -->")
        code, out = self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.assertEqual(code, 2)

    def test_forged_receipt_edit_detected(self):
        self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.advance(self.cid, "design")
        approvals = self.change_dir() / "approvals.toml"
        approvals.write_text(approvals.read_text().replace('approver = "alice"', 'approver = "mallory"'))
        code, out = self.cli("check")
        self.assertIn("is not authorized", out)

    def test_audit_chain_tamper_detected(self):
        self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        log = self.change_dir() / "audit.jsonl"
        lines = log.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["risk"] = "high"
        lines[0] = json.dumps(entry, sort_keys=True)
        log.write_text("\n".join(lines) + "\n")
        code, out = self.cli("audit", "verify")
        self.assertEqual(code, 1)
        self.assertIn("hash chain broken", out)

    def test_audit_append_only_against_base(self):
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "chore: base", "--no-verify")
        log = self.change_dir() / "audit.jsonl"
        log.write_text("")  # truncate history
        code, out = self.cli("audit", "verify", "--base", "HEAD")
        self.assertIn("append-only", out)

    def test_codeowners_generated_from_roster(self):
        code, out = self.cli("codeowners")
        self.assertEqual(code, 0, out)
        text = (self.repo / ".github/CODEOWNERS").read_text()
        self.assertIn("/docs/changes/*/spec.md", text)
        self.assertIn("@alice @tina", text)
        self.assertLess(text.index("*  "), text.index("/docs/changes/*/spec.md"))
        self.assertEqual(self.cli("codeowners", "--check")[0], 0)
        self.set_roster(security=["sam"])
        self.assertEqual(self.cli("codeowners", "--check")[0], 1)


class SingleMaintainerTests(HarnessCase):
    """With separation_of_duties = false a verified commit signature replaces the platform review.

    GitHub forbids approving your own pull request, so the documented single-maintainer mode was unreachable
    (field feedback, v0.6): every pull request adding a receipt failed. The receipt alone would be a file the
    author wrote, so the binding to a checked identity moves to the commit signature.
    """

    def setUp(self):
        super().setUp()
        self.set_roster(product_owner=["solo"])
        roster = self.repo / ".harness/roster.toml"
        roster.write_text(roster.read_text().replace("separation_of_duties = true", "separation_of_duties = false"))
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "chore: base", "--no-verify")
        sh(self.repo, "git", "checkout", "-qb", "feature")
        self.cid = self.new_change(risk="low")
        self.write_valid("spec.md")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "docs: spec", "--no-verify")
        self.cli("approve", self.cid, "spec.md", "--as", "solo", "--role", "product-owner")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "docs: approve spec", "--no-verify")
        self.head = sh(self.repo, "git", "rev-parse", "HEAD")

    def verify(self, client):
        return platform.verify(self.repo, client, "main")

    def test_signed_receipt_is_accepted_without_a_platform_review(self):
        report = self.verify(FakeClient({}, signatures={self.head: (True, "solo")}))
        self.assertEqual(report.errors, [])

    def test_unsigned_receipt_is_rejected(self):
        report = self.verify(FakeClient({}))
        self.assertIn("must have a signature the platform verifies", report.errors[0])

    def test_a_signature_from_someone_else_is_rejected(self):
        report = self.verify(FakeClient({}, signatures={self.head: (True, "mallory")}))
        self.assertIn("is signed by 'mallory'", report.errors[0])

    def test_a_platform_review_still_works_when_there_is_one(self):
        report = self.verify(FakeClient({"solo": self.head}))
        self.assertEqual(report.errors, [])

    def test_separation_of_duties_still_requires_a_review(self):
        roster = self.repo / ".harness/roster.toml"
        roster.write_text(roster.read_text().replace("separation_of_duties = false", "separation_of_duties = true"))
        report = self.verify(FakeClient({}, signatures={self.head: (True, "solo")}))
        self.assertIn("no current approval", report.errors[0])


class PlatformVerifyTests(HarnessCase):
    def setUp(self):
        super().setUp()
        self.set_roster(product_owner=["alice", "@acme/product"])
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", "chore: base", "--no-verify")
        sh(self.repo, "git", "checkout", "-qb", "feature")
        self.cid = self.new_change(risk="low")
        self.write_valid("spec.md")
        self.commit("docs: spec")
        self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.approved_at = self.commit("docs: approve spec")

    def commit(self, msg):
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", msg, "--no-verify")
        return sh(self.repo, "git", "rev-parse", "HEAD")

    def verify(self, client):
        return platform.verify(self.repo, client, "main")

    def test_valid_platform_approval(self):
        report = self.verify(FakeClient({"alice": self.approved_at}))
        self.assertEqual(report.errors, [])

    def test_missing_platform_approval(self):
        report = self.verify(FakeClient({}))
        self.assertIn("no current approval", report.errors[0])

    def test_approval_on_older_commit_without_receipt(self):
        first = sh(self.repo, "git", "rev-parse", "HEAD~1")
        report = self.verify(FakeClient({"alice": first}))
        self.assertIn("receipt was added after the approval", report.errors[0])

    def test_content_changed_after_platform_approval(self):
        (self.change_dir() / "spec.md").write_text(VALID["spec.md"] + "\nchanged\n")
        self.commit("docs: change")
        self.cli("approve", self.cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.commit("docs: re-receipt without re-review")
        report = self.verify(FakeClient({"alice": self.approved_at}))
        self.assertIn("different content", report.errors[0])

    def test_separation_of_duties(self):
        report = self.verify(FakeClient({"alice": self.approved_at}, pr_author="alice"))
        self.assertIn("separation of duties", report.errors[0])
        spec_commit = sh(self.repo, "git", "rev-parse", "HEAD~1")
        report = self.verify(FakeClient({"alice": self.approved_at}, authors={spec_commit: "alice"}))
        self.assertIn("separation of duties", report.errors[0])

    def test_team_membership_resolved_on_platform(self):
        approvals = self.change_dir() / "approvals.toml"
        approvals.write_text(approvals.read_text().replace('"alice"', '"bob"'))
        head = self.commit("docs: bob receipt")
        self.assertIn("not a member", self.verify(FakeClient({"bob": head})).errors[0])
        report = self.verify(FakeClient({"bob": head}, teams={"@acme/product": ["bob"]}))
        self.assertEqual(report.errors, [])

    def test_receipts_already_on_base_are_not_reverified(self):
        sh(self.repo, "git", "checkout", "-q", "main")
        sh(self.repo, "git", "merge", "-q", "feature")
        report = self.verify(FakeClient({}))
        self.assertEqual(report.errors, [])


if __name__ == "__main__":
    unittest.main()
