import datetime as dt
import json
import unittest

from helpers import HarnessCase, sh

from sdlc_harness import architecture, contracts, yamlish


class GitCase(HarnessCase):
    def setUp(self):
        super().setUp()
        self.commit("chore: base")
        sh(self.repo, "git", "checkout", "-qb", "work")

    def commit(self, msg, files=None):
        for path, content in (files or {}).items():
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                target.unlink()
            else:
                target.write_text(content)
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "commit", "-qm", msg, "--no-verify", "--allow-empty")


class TestFirstTests(GitCase):
    def test_source_before_test_is_flagged(self):
        self.commit("feat: add pay", {"src/pay.py": "def pay(): pass\n"})
        self.commit("test: cover pay", {"tests/test_pay.py": "def test_pay(): pass\n"})
        code, out = self.cli("tdd", "--base", "main")
        self.assertEqual(code, 1)
        self.assertIn("changes source before any test change", out)

    def test_test_first_or_together_passes(self):
        self.commit("test: failing test", {"tests/test_pay.py": "def test_pay(): assert False\n"})
        self.commit("feat: add pay", {"src/pay.py": "def pay(): pass\n"})
        self.commit("fix: pay rounding", {"src/pay.py": "def pay(): return 1\n", "tests/test_pay.py": "x = 1\n"})
        code, out = self.cli("tdd", "--base", "main")
        self.assertEqual(code, 0, out)

    def test_refactor_and_waiver_are_allowed(self):
        self.commit("refactor: rename", {"src/a.py": "x = 1\n"})
        self.commit("feat: spike\n\nTDD-Waiver: throwaway prototype approved by lead", {"src/b.py": "y = 2\n"})
        code, out = self.cli("tdd", "--base", "main")
        self.assertEqual(code, 0, out)
        self.assertIn("waived", out)


class WeakenedTestsTests(GitCase):
    def setUp(self):
        super().setUp()
        self.commit("test: base tests", {
            "tests/test_a.py": "def test_a():\n    assert 1\n",
            "web/app.spec.ts": "it('works', () => {})\n",
            "api/handler_test.go": "func TestX(t *testing.T) {}\n",
        })
        sh(self.repo, "git", "branch", "-f", "main", "HEAD")

    def test_skip_markers_and_deleted_tests(self):
        self.commit("feat: stuff", {
            "tests/test_a.py": "import pytest\n@pytest.mark.skip\ndef test_a():\n    assert 1\n",
            "web/app.spec.ts": "it.only('works', () => {})\n",
            "api/handler_test.go": None,
        })
        code, out = self.cli("tdd", "--base", "main")
        self.assertEqual(code, 1)
        self.assertIn("python skip/xfail", out)
        self.assertIn("js/ts skip/only/focus", out)
        self.assertIn("test file deleted: api/handler_test.go", out)

    def test_waiver_downgrades_to_warning(self):
        self.commit("test: quarantine flaky\n\nTest-Waiver: flaky upstream sandbox, ISSUE-9",
                    {"tests/test_a.py": "import unittest\n@unittest.skip('flaky')\ndef test_a(): pass\n"})
        code, out = self.cli("tdd", "--base", "main")
        self.assertEqual(code, 0, out)
        self.assertIn("waived: flaky upstream sandbox", out)

    def test_check_base_applies_profile_levels(self):
        self.commit("feat: skip", {"web/app.spec.ts": "xit('works', () => {})\n"})
        code, out = self.cli("check", "--base", "main")
        self.assertEqual(code, 1)
        self.assertIn("weakened test", out)


def sarif(results, rules=None, tool="scanner"):
    return json.dumps({"version": "2.1.0", "runs": [{"tool": {"driver": {"name": tool, "rules": rules or []}},
                                                      "results": results}]})


def result(rule, uri="src/app.py", level=None, **props):
    r = {"ruleId": rule, "message": {"text": f"{rule} found"},
         "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}}}]}
    if level:
        r["level"] = level
    if props:
        r["properties"] = props
    return r


class EvidenceTests(HarnessCase):
    def setUp(self):
        super().setUp()
        self.dir = self.repo / "sdlc-evidence"
        self.dir.mkdir()

    def write(self, name, content):
        (self.dir / name).write_text(content)

    def complete_set(self):
        self.write("secrets.sarif", sarif([]))
        self.write("sast.sarif", sarif([]))
        self.write("sca.sarif", sarif([]))
        self.write("sbom.json", json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "x", "version": "1"}]}))

    def test_missing_required_evidence(self):
        code, out = self.cli("evidence", "check")
        self.assertEqual(code, 1)
        for kind in ("secrets", "sast", "sca", "sbom"):
            self.assertIn(f"missing evidence '{kind}'", out)

    def test_severity_threshold_from_scores_levels_and_secrets(self):
        self.complete_set()
        self.write("sca.sarif", sarif(
            [result("CVE-1"), result("CVE-2")],
            rules=[{"id": "CVE-1", "properties": {"security-severity": "9.8"}},
                   {"id": "CVE-2", "properties": {"security-severity": "5.0"}}], tool="Trivy"))
        self.write("sast.sarif", sarif([result("rule.warn", level="warning"), result("rule.err", level="error")]))
        self.write("secrets.sarif", sarif([result("aws-access-token", uri=".env")], tool="gitleaks"))
        code, out = self.cli("evidence", "check")
        self.assertEqual(code, 1)
        self.assertIn("critical CVE-1", out)
        self.assertNotIn("CVE-2", out)
        self.assertIn("high rule.err", out)
        self.assertNotIn("rule.warn", out)
        self.assertIn("critical aws-access-token at .env", out)

    def test_suppressed_results_ignored(self):
        self.complete_set()
        r = result("rule.err", level="error")
        r["suppressions"] = [{"kind": "inSource"}]
        self.write("sast.sarif", sarif([r]))
        self.assertEqual(self.cli("evidence", "check")[0], 0)

    def test_exceptions_valid_and_expired(self):
        self.complete_set()
        self.write("sast.sarif", sarif([result("py.eval", uri="tools/legacy/run.py", level="error")]))
        future = dt.date.today() + dt.timedelta(days=30)
        exc = self.repo / ".harness/exceptions.toml"
        exc.write_text(f'[[exception]]\nrule = "py.*"\npath = "tools/legacy/*"\nreason = "allowlist"\n'
                       f'approver = "sam"\nexpires = {future.isoformat()}\n')
        code, out = self.cli("evidence", "check")
        self.assertEqual(code, 0, out)
        self.assertIn("excepted until", out)
        exc.write_text(exc.read_text().replace(future.isoformat(), "2020-01-01"))
        code, out = self.cli("evidence", "check")
        self.assertEqual(code, 1)
        self.assertIn("expired on 2020-01-01", out)

    def test_denied_license_in_sbom(self):
        self.complete_set()
        self.write("sbom.json", json.dumps({"bomFormat": "CycloneDX", "components": [
            {"name": "ok", "version": "1", "licenses": [{"license": {"id": "MIT"}}]},
            {"name": "bad", "version": "2", "purl": "pkg:npm/bad@2",
             "licenses": [{"expression": "(MIT OR AGPL-3.0-only)"}]}]}))
        code, out = self.cli("evidence", "check")
        self.assertEqual(code, 1)
        self.assertIn("pkg:npm/bad@2: license (MIT OR AGPL-3.0-only) is denied", out)

    def test_require_override(self):
        self.write("sbom.json", json.dumps({"bomFormat": "CycloneDX", "components": []}))
        code, out = self.cli("evidence", "check", "--require", "sbom")
        self.assertEqual(code, 0, out)


class ArchitectureTests(HarnessCase):
    RULES = """
[[layers]]
name = "domain"
paths = ["src/app/domain/**", "web/src/domain/**", "internal/domain/**", "java/com/acme/domain/**"]
modules = ["app.domain", "@/domain", "github.com/acme/svc/internal/domain", "com.acme.domain"]

[[layers]]
name = "adapters"
paths = ["src/app/adapters/**", "web/src/adapters/**", "internal/adapters/**", "java/com/acme/adapters/**"]
modules = ["app.adapters", "@/adapters", "github.com/acme/svc/internal/adapters", "com.acme.adapters"]

[[rules]]
layer = "domain"
forbid_layers = ["adapters"]
forbid_imports = ["requests", "axios"]
adr = "docs/adr/0001-hexagonal.md"
"""

    def setUp(self):
        super().setUp()
        (self.repo / ".harness/architecture.toml").write_text(self.RULES)
        (self.repo / "docs/adr/0001-hexagonal.md").write_text("# 0001\n\n**Status:** Accepted\n")
        files = {
            "src/app/domain/order.py": "from app.adapters.db import save\nimport requests\nfrom . import money\n",
            "src/app/domain/money.py": "from ..adapters import http\n",
            "src/app/adapters/db.py": "from app.domain.order import Order\n",
            "web/src/domain/cart.ts": "import { api } from '../adapters/api'\nimport axios from 'axios'\n"
                                      "import { x } from '@/domain/x'\n",
            "internal/domain/svc.go": 'package domain\n\nimport (\n\t"fmt"\n\tdb "github.com/acme/svc/internal/adapters/db"\n)\n',
            "java/com/acme/domain/Order.java": "package com.acme.domain;\nimport com.acme.adapters.Repo;\n",
        }
        for path, content in files.items():
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(content)
        sh(self.repo, "git", "add", "-A")

    def test_violations_across_languages(self):
        code, out = self.cli("arch")
        self.assertEqual(code, 1)
        expected = [
            "src/app/domain/order.py:1: layer 'domain' must not depend on 'adapters' (app.adapters.db)",
            "src/app/domain/order.py:2: layer 'domain' must not import 'requests'",
            "src/app/domain/money.py:1: layer 'domain' must not depend on 'adapters'",
            "web/src/domain/cart.ts:1: layer 'domain' must not depend on 'adapters'",
            "web/src/domain/cart.ts:2: layer 'domain' must not import 'axios'",
            "internal/domain/svc.go:5: layer 'domain' must not depend on 'adapters'",
            "java/com/acme/domain/Order.java:2: layer 'domain' must not depend on 'adapters'",
        ]
        for e in expected:
            self.assertIn(e, out)
        self.assertNotIn("adapters/db.py", out)
        self.assertEqual(out.count("ERROR"), len(expected))

    def test_unknown_layer_and_missing_adr(self):
        (self.repo / ".harness/architecture.toml").write_text(
            self.RULES.replace('forbid_layers = ["adapters"]', 'forbid_layers = ["infra"]')
            .replace("0001-hexagonal", "0009-missing"))
        report = architecture.check(self.repo)
        self.assertTrue(any("unknown layer 'infra'" in e for e in report.errors))
        self.assertTrue(any("missing ADR" in e for e in report.errors))


OPENAPI_V1 = """
openapi: 3.0.3
info:
  title: Orders
  version: 1.4.0
paths:
  /orders/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema: {type: string}
    get:
      parameters:
        - name: expand
          in: query
          schema:
            type: string
            enum: [items, customer]
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        "404":
          description: missing
    delete:
      responses:
        "204": {description: deleted}
  /orders:
    post:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                sku: {type: string, maxLength: 64}
                qty: {type: integer}
              required: [sku]
      responses:
        "201": {description: created}
components:
  schemas:
    Order:
      type: object
      required: [id, status]
      properties:
        id: {type: string}
        status:
          type: string
          enum: [open, paid]
        total: {type: number}
"""


class ContractTests(unittest.TestCase):
    def breaking(self, old, new):
        return contracts.diff(yamlish.loads(old), yamlish.loads(new)).breaking

    def test_compatible_additions(self):
        new = OPENAPI_V1.replace("        total: {type: number}", "        total: {type: number}\n        note: {type: string}")
        new = new.replace("                qty: {type: integer}", "                qty: {type: integer}\n                gift: {type: boolean}")
        self.assertEqual(self.breaking(OPENAPI_V1, new), [])

    def test_breaking_changes_detected(self):
        new = (OPENAPI_V1
               .replace("    delete:\n      responses:\n        \"204\": {description: deleted}\n", "")
               .replace("              required: [sku]", "              required: [sku, qty]")
               .replace("maxLength: 64", "maxLength: 32")
               .replace("      required: [id, status]", "      required: [id]")
               .replace("          enum: [open, paid]", "          enum: [open, paid, refunded]")
               .replace("        total: {type: number}", "        total: {type: string}")
               .replace("            enum: [items, customer]", "            enum: [items]"))
        found = "\n".join(self.breaking(OPENAPI_V1, new))
        for fragment in ["DELETE /orders/{id}: operation removed",
                         "property 'qty' is now required",
                         "maxLength tightened 64 -> 32",
                         "property 'status' is no longer guaranteed",
                         "new enum values may be returned: ['refunded']",
                         "total: type changed ['number'] -> ['string']",
                         "enum values no longer accepted: ['customer']"]:
            self.assertIn(fragment, found)

    def test_asyncapi_2_and_3(self):
        v2 = """
asyncapi: 2.6.0
info: {title: Lights, version: 1.0.0}
channels:
  light/measured:
    subscribe:
      message:
        name: lightMeasured
        payload:
          type: object
          required: [lumens]
          properties:
            lumens: {type: integer}
  light/on:
    publish:
      message:
        name: turnOn
        payload: {type: object, properties: {id: {type: string}}}
"""
        new2 = v2.replace("          required: [lumens]\n", "").replace("  light/on:", "  light/switch:")
        found = "\n".join(self.breaking(v2, new2))
        self.assertIn("channel light/on: channel removed", found)
        self.assertIn("'lumens' is no longer guaranteed", found)

        v3 = """
asyncapi: 3.0.0
info: {title: Lights, version: 1.0.0}
channels:
  measured:
    address: light/measured
    messages:
      lightMeasured:
        payload:
          type: object
          properties:
            lumens: {type: integer}
operations:
  sendMeasurement:
    action: send
    channel: {$ref: '#/channels/measured'}
"""
        new3 = v3.replace("lumens: {type: integer}", "lux: {type: integer}")
        self.assertIn("property 'lumens' removed from response", "\n".join(self.breaking(v3, new3)))


class ContractGateTests(GitCase):
    def test_major_bump_allows_breaking_change(self):
        cfg = self.repo / "harness.toml"
        cfg.write_text(cfg.read_text().replace('files = []\n\n[evidence]', 'files = ["api/openapi.yaml"]\n\n[evidence]'))
        self.commit("feat: contract", {"api/openapi.yaml": OPENAPI_V1})
        sh(self.repo, "git", "branch", "-f", "main", "HEAD")
        broken = OPENAPI_V1.replace("  /orders:\n    post:", "  /orders-v2:\n    post:")
        self.commit("feat!: move orders", {"api/openapi.yaml": broken})
        code, out = self.cli("contracts", "--base", "main")
        self.assertEqual(code, 1)
        self.assertIn("breaking change without major version bump: /orders: path removed", out)
        self.commit("feat!: bump", {"api/openapi.yaml": broken.replace("version: 1.4.0", "version: 2.0.0")})
        code, out = self.cli("contracts", "--base", "main")
        self.assertEqual(code, 0, out)
        self.assertIn("allowed by version 1.4.0 -> 2.0.0", out)


class YamlishTests(unittest.TestCase):
    def test_subset(self):
        text = """
# comment
a: 1
b: "x: #not comment"
c: 'it''s'
d: [1, two, {k: v}]
e:
  - name: n
    v: true
  - - nested
    - list
f: |
  line1
  line2
g: >-
  folded
  text
h: ~
i: plain
  continued
"""
        self.assertEqual(yamlish.loads(text), {
            "a": 1, "b": "x: #not comment", "c": "it's", "d": [1, "two", {"k": "v"}],
            "e": [{"name": "n", "v": True}, ["nested", "list"]], "f": "line1\nline2\n", "g": "folded text",
            "h": None, "i": "plain continued"})

    def test_rejects_anchors(self):
        with self.assertRaises(yamlish.YamlError):
            yamlish.loads("a: &x 1\nb: *x\n")


if __name__ == "__main__":
    unittest.main()
