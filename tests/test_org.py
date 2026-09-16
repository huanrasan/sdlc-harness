import datetime as dt
import io
import json
import unittest
from pathlib import Path

from helpers import HarnessCase, sh

from sdlc_harness import mcp

POLICY = """
[policy]
id = "acme-baseline"
version = "1.2.0"

[require]
min_profile = "standard"
sensors = { weakened_tests = "error", test_first = "error" }
require_evidence = ["secrets", "sbom"]
license_deny = ["AGPL-3.0-only", "SSPL-1.0"]
fail_on_max = "high"
approvals = ["spec.md"]
separation_of_duties = true
agents_md_lines = ["Never run `sdlc approve`"]

[recommend]
roles_with_members = ["security"]
"""


class OrgPolicyTests(HarnessCase):
    def setUp(self):
        super().setUp()
        self.org = Path(self.tmp.name) / "org"
        (self.org / "skills/org-cloud-baseline").mkdir(parents=True)
        (self.org / "memory").mkdir()
        (self.org / "policy.toml").write_text(POLICY)
        (self.org / "skills/org-cloud-baseline/SKILL.md").write_text(
            "---\nname: org-cloud-baseline\ndescription: Organization landing zone rules for any cloud.\n---\nbody\n")
        (self.org / "memory/MEM-2026-01-01-tag-everything.md").write_text(
            "---\nid: MEM-2026-01-01-tag-everything\ntype: convention\ntitle: Tag every cloud resource with team and cost center\n"
            "tags: finops, cloud\nsource: org\ncreated: 2026-01-01\nreview_by: 2099-01-01\nstatus: active\n"
            "superseded_by:\n---\nAll infrastructure carries team and cost-center labels.\n")
        sh(self.org, "git", "init", "-q")
        sh(self.org, "git", "add", "-A")
        sh(self.org, "git", "-c", "user.email=o@o", "-c", "user.name=o", "commit", "-qm", "policy")

    def pull(self):
        code, out = self.cli("org", "pull", "--source", str(self.org))
        self.assertEqual(code, 0, out)
        self.cli("sync")

    def test_pull_vendors_policy_skills_and_memory_and_standard_complies(self):
        self.pull()
        lock = (self.repo / ".harness/org/lock.toml").read_text()
        self.assertIn(".agents/skills/org-cloud-baseline/SKILL.md", lock)
        self.assertIn("`org-cloud-baseline`", (self.repo / "AGENTS.md").read_text())
        code, out = self.cli("check")
        # standard profile has test_first = warn, below the organization minimum
        self.assertEqual(code, 1)
        self.assertIn("sensor 'test_first' is 'warn', organization requires at least 'error'", out)
        self.assertNotIn("weakened_tests", out.split("organization requires")[0].split("ERROR")[-1])
        self.assertIn("(recommended): roster role 'security' must have members", out)

    def test_violations_and_deviation(self):
        self.pull()
        cfg = self.repo / "harness.toml"
        cfg.write_text(cfg.read_text().replace('fail_on = "high"', 'fail_on = "critical"')
                       .replace('"AGPL-3.0-only", ', ""))
        code, out = self.cli("check")
        self.assertIn("fail_on 'critical' is looser than organization 'high'", out)
        self.assertIn("license 'AGPL-3.0-only' must be in [evidence] license_deny", out)

        self.set_roster(architect=["ana"])
        future = (dt.date.today() + dt.timedelta(days=60)).isoformat()
        (self.repo / ".harness/deviations.toml").write_text(
            f'[[deviation]]\npolicy = "sensors.test_first"\nreason = "legacy module"\napprover = "ana"\n'
            f'role = "architect"\nexpires = {future}\n'
            f'[[deviation]]\npolicy = "fail_on_max"\nreason = "noisy scanner"\napprover = "bob"\n'
            f'role = "architect"\nexpires = {future}\n'
            f'[[deviation]]\npolicy = "min_profile"\nreason = "not needed"\napprover = "ana"\n'
            f'role = "architect"\nexpires = {future}\n')
        code, out = self.cli("check")
        self.assertIn("deviation until", out)
        self.assertIn("'bob' is not a member of role 'architect'", out)
        self.assertIn("deviation 'min_profile' is no longer needed", out)

    def test_lite_below_min_profile(self):
        self.pull()
        cfg = self.repo / "harness.toml"
        cfg.write_text(cfg.read_text().replace('profile = "standard"', 'profile = "lite"'))
        code, out = self.cli("check")
        self.assertIn("profile 'lite' is below the organization minimum 'standard'", out)

    def test_local_edits_to_vendored_files_detected(self):
        self.pull()
        skill = self.repo / ".agents/skills/org-cloud-baseline/SKILL.md"
        skill.write_text(skill.read_text() + "\nlocal tweak\n")
        code, out = self.cli("check")
        self.assertIn("modified locally", out)

    def test_org_skills_must_be_prefixed(self):
        (self.org / "skills/org-cloud-baseline").rename(self.org / "skills/cloud")
        code, out = self.cli("org", "pull", "--source", str(self.org))
        self.assertEqual(code, 2)
        self.assertIn("must be prefixed 'org-'", out)


class MemoryTests(HarnessCase):
    def test_add_search_index_and_check(self):
        code, out = self.cli("memory", "add", "--type", "pitfall", "--title", "Retries need idempotency keys",
                             "--tags", "payments,retries", "--body", "Duplicate charges happened when retrying.",
                             "--source", "docs/changes/2026-09-16-retries")
        self.assertEqual(code, 0, out)
        code, out = self.cli("memory", "search", "retry idempotency")
        self.assertIn("Retries need idempotency keys", out)
        self.assertIn("Retries need idempotency keys", (self.repo / "docs/memory/INDEX.md").read_text())
        self.assertEqual(self.cli("check")[0], 0)

    def test_secret_rejected_and_stale_index(self):
        code, out = self.cli("memory", "add", "--type", "lesson", "--title", "Deploy key",
                             "--body", "use token: ghp_" + "a" * 36)
        self.assertEqual(code, 2)
        self.assertIn("secret", out)
        (self.repo / "docs/memory/MEM-2026-01-01-manual.md").write_text(
            "---\nid: MEM-2026-01-01-manual\ntype: lesson\ntitle: Manual\ntags: x\nsource:\ncreated: 2026-01-01\n"
            "review_by: 2026-02-01\nstatus: active\nsuperseded_by:\n---\npassword = hunter2hunter2\n")
        code, out = self.cli("check")
        self.assertIn("looks like it contains a secret", out)
        self.assertIn("review date passed", out)
        self.assertIn("INDEX.md is stale", out)


class McpTests(HarnessCase):
    def rpc(self, *messages):
        stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = io.StringIO()
        mcp.serve(self.repo, stdin, stdout)
        return [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_protocol_and_tools(self):
        responses = self.rpc(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "memory_add", "arguments": {
                "type": "convention", "title": "Use expand contract migrations", "tags": ["data"],
                "body": "Never drop columns in the same release."}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "memory_search",
                                                                          "arguments": {"query": "migrations"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "check", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 6, "method": "approve"},
        )
        self.assertEqual(len(responses), 6)
        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "sdlc-harness")
        names = {t["name"] for t in responses[1]["result"]["tools"]}
        self.assertEqual(names, {"memory_search", "memory_add", "change_status", "check", "trace"})
        self.assertNotIn("approve", " ".join(names))
        self.assertIn("created docs/memory/", responses[2]["result"]["content"][0]["text"])
        self.assertIn("Use expand contract migrations", responses[3]["result"]["content"][0]["text"])
        self.assertFalse(responses[4]["result"]["isError"], responses[4]["result"]["content"][0]["text"])
        self.assertEqual(responses[5]["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
