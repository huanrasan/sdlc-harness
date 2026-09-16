import json
import os
import unittest

from helpers import VALID, HarnessCase, sh


class TraceTests(HarnessCase):
    profile = "lite"

    def test_trace_links_criteria_tests_results_approvals_and_commits(self):
        cid = self.new_change(risk="low")
        for name in ("spec.md", "plan.md", "threat-model.md", "verification.md"):
            (self.change_dir() / name).write_text(VALID[name])
        spec = self.change_dir() / "spec.md"
        spec.write_text(spec.read_text().replace("| AC-1 |", "| AC-2 | Given x, when y, then z | test |\n| AC-1 |"))
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", f"feat: retries\n\nChange: {cid}", "--no-verify")
        code, out = self.cli("report", "trace", "--change", cid, "--format", "json")
        self.assertEqual(code, 0, out)
        data = json.loads(out)
        ac1 = next(c for c in data["criteria"] if c["id"] == "AC-1")
        self.assertEqual(ac1["tests"], ["test_retry"])
        self.assertEqual(ac1["result"], "pass")
        self.assertEqual(data["threats"][0]["control"], "idempotency key")
        self.assertIn("AC-2 has no planned test", data["gaps"])
        self.assertIn("AC-2 not verified", data["gaps"])
        self.assertEqual(data["commits"][0]["subject"], "feat: retries")


class FlowTests(HarnessCase):
    def test_flow_counts_blocks_phases_and_approvals(self):
        self.set_roster(product_owner=["alice"])
        cid = self.new_change(risk="low")
        self.write_valid("spec.md")
        self.cli("phase", cid, "design")  # blocked: needs approval
        self.cli("approve", cid, "spec.md", "--as", "alice", "--role", "product-owner")
        self.advance(cid, "design")
        code, out = self.cli("report", "flow", "--format", "json")
        data = json.loads(out)
        row = data["changes"][0]
        self.assertEqual(row["gate_blocks"], 1)
        self.assertIn("spec", row["hours_in_phase"])
        self.assertEqual(data["summary"]["gate_blocks_by_target_phase"], {"design": 1})
        self.assertEqual(data["summary"]["approvals_by_role"], {"product-owner": 1})
        code, html = self.cli("report", "flow", "--format", "html")
        self.assertIn("<table>", html)
        self.assertIn("prefers-color-scheme: dark", html)


class DoraTests(HarnessCase):
    def commit_at(self, when, msg):
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        import subprocess
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", msg, "--no-verify"], cwd=self.repo, env=env,
                       check=True)

    def tag_at(self, when, tag):
        env = {**os.environ, "GIT_COMMITTER_DATE": when}
        import subprocess
        subprocess.run(["git", "tag", "-a", tag, "-m", tag], cwd=self.repo, env=env, check=True)

    def test_dora_metrics_from_tags(self):
        self.commit_at("2026-01-01T10:00:00+00:00", "feat: a")
        self.tag_at("2026-01-02T10:00:00+00:00", "v1.0.0")
        self.commit_at("2026-01-05T10:00:00+00:00", "feat: b")
        self.tag_at("2026-01-06T10:00:00+00:00", "v1.1.0")
        self.commit_at("2026-01-06T12:00:00+00:00", "fix: b broke checkout")
        self.tag_at("2026-01-06T16:00:00+00:00", "v1.1.1")
        self.commit_at("2026-01-10T10:00:00+00:00", "feat: c")
        self.tag_at("2026-01-12T10:00:00+00:00", "v1.2.0")
        code, out = self.cli("report", "dora", "--since", "2026-01-01", "--format", "json")
        data = json.loads(out)
        self.assertEqual(data["releases"], 4)
        self.assertEqual(data["failed_releases"], ["v1.1.0"])
        self.assertEqual(data["rework_releases"], ["v1.1.1"])
        self.assertEqual(data["change_failure_rate"], 0.25)
        self.assertEqual(data["median_failed_deployment_recovery_hours"], 6.0)
        self.assertEqual(data["median_lead_time_hours"], 24.0)


if __name__ == "__main__":
    unittest.main()
