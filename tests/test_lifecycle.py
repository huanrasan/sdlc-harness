import unittest

from helpers import HarnessCase

FILLED = {
    "discovery.md": """# Discovery
## Problem
Checkout abandonment is 30% on mobile (analytics, Q2).
## Target users
Mobile buyers.
## Success metrics
| Metric | Baseline | Target | Measured by |
|---|---|---|---|
| mobile checkout conversion | 70% | 78% | product analytics |
## Options
| Option | Summary | Value | Effort | Risk |
|---|---|---|---|---|
| Do nothing | keep | none | none | low |
| One-page checkout | merge steps | high | medium | medium |
## Decision
Decision: go
First increment: guest checkout.
""",
    "ux.md": """# UX
## User flows
Guest checkout covers AC-1.
## Screens and states
| Screen / component | Empty | Loading | Error | Success | Design reference |
|---|---|---|---|---|---|
| Checkout form | n/a | spinner | inline errors | receipt | ds/checkout |
## Accessibility (WCAG 2.2 AA)
- [x] Keyboard operable, visible focus, logical order
## Validation
Prototype tested with 5 users.
""",
    "data.md": """# Data
## Data changes
| Entity / dataset | Change | Classification (public, internal, confidential, restricted) | Owner |
|---|---|---|---|
| guest_orders | new table | confidential | payments |
## Migrations
Expand only.
## Rollback
Drop table before launch.
## Retention and lineage
7 years (tax); feeds finance export.
## Privacy impact (required when the change declares the personal-data scope)
| Question | Answer |
|---|---|
| Personal data categories | email, address |
| Purpose and lawful basis | contract |
""",
    "cost.md": """# Cost
## Estimate
| Component | Pricing driver (unit) | Assumed volume | Monthly cost | Environment |
|---|---|---|---|---|
| database | GB-month | 50 GB | 25 USD | production |

Total monthly (production): 25 USD
Total monthly (non-production): 5 USD

## Assumptions
Price list 2026-09.
## Guardrails
- Budget and alert thresholds: 50 USD, alert at 80%
- Cost allocation tags or labels: team=payments
- Scale-down / idle policy for non-production: nightly stop
""",
    "ai-risk.md": """# AI risk
## Use case
Summarize support tickets; suggests only.
## Risk classification
Low, internal tool.
## Risks
| ID | Risk (OWASP LLM / Agentic category) | Impact | Mitigation | Verifiable by |
|---|---|---|---|---|
| R-1 | prompt injection | wrong summary | no tool access, output shown as draft | red-team eval |
## Evaluations
| Eval | Dataset / scenarios | Metric | Threshold | Result |
|---|---|---|---|---|
| faithfulness | 200 tickets | score | 0.9 | 0.93 |
## Human oversight
Agent edits every summary.
## Data and privacy
No retention by provider.
## Monitoring
Thumbs-down rate.
""",
    "outcome.md": """# Outcome
## Results against success metrics
| Metric | Baseline | Target | Actual | Measured on |
|---|---|---|---|---|
| mobile checkout conversion | 70% | 78% | 76% | 2026-10-30 |
## Decision
Decision: iterate
""",
    "retirement.md": """# Retirement
## What is retired
API v1.
## Consumers
| Consumer | Contact | Migration path | Status |
|---|---|---|---|
| mobile app 3.x | team-mobile | move to v2 | done |
## Timeline
| Milestone | Date (YYYY-MM-DD) |
|---|---|
| Deprecation notice | 2026-10-01 |
| Sunset | 2027-01-15 |
## Data disposition
Nothing stored.
## Contracts and dependencies
Sunset header, revoke v1 keys.
## Infrastructure teardown
Destroy v1 gateway via IaC.
## Rollback
Redeploy v1 image before sunset.
""",
}


class LifecycleTests(HarnessCase):
    profile = "lite"

    def setUp(self):
        super().setUp()
        rules = "".join(
            f'\n[[rules]]\nartifact = "{a}"\nphase = "{p}"\ntypes = {t}\nmin_risk = "low"\n' + (f"scopes = {s}\n" if s else "")
            for a, p, t, s in [
                ("discovery.md", "discover", '["feature"]', None),
                ("ux.md", "design", '["feature"]', '["ui"]'),
                ("data.md", "design", '["feature"]', '["data", "personal-data"]'),
                ("cost.md", "design", '["feature"]', '["infra"]'),
                ("ai-risk.md", "design", '["feature"]', '["ai"]'),
                ("outcome.md", "operate", '["feature"]', None),
                ("retirement.md", "design", '["retirement"]', None),
            ])
        (self.repo / ".harness/profiles/lite.toml").write_text(rules)

    def set_phase(self, phase):
        meta = self.change_dir() / "change.toml"
        text = meta.read_text()
        current = next(line for line in text.splitlines() if line.startswith("phase = "))
        meta.write_text(text.replace(current, f'phase = "{phase}"'))

    def test_start_phase_and_scoped_templates(self):
        code, out = self.cli("new", "feature", "checkout", "--risk", "low", "--scope", "ui,personal-data")
        self.assertEqual(code, 0, out)
        meta = (self.change_dir() / "change.toml").read_text()
        self.assertIn('phase = "discover"', meta)
        self.assertIn('scopes = ["ui", "personal-data"]', meta)
        files = {p.name for p in self.change_dir().iterdir()}
        self.assertTrue({"discovery.md", "ux.md", "data.md", "outcome.md"} <= files)
        self.assertFalse({"cost.md", "ai-risk.md"} & files)

    def test_fix_starts_at_spec_and_unknown_scope_rejected(self):
        self.new_change(change_type="fix", risk="low")
        self.assertIn('phase = "spec"', (self.change_dir() / "change.toml").read_text())
        code, out = self.cli("new", "feature", "other", "--scope", "mobile")
        self.assertEqual(code, 2)
        self.assertIn("unknown scopes", out)

    def test_all_new_artifacts_pass_when_complete(self):
        self.cli("new", "feature", "checkout", "--risk", "low", "--scope", "ui,personal-data,infra,ai")
        for name in ("discovery.md", "ux.md", "data.md", "cost.md", "ai-risk.md", "outcome.md"):
            (self.change_dir() / name).write_text(FILLED[name])
        self.set_phase("done")
        code, out = self.cli("check")
        self.assertEqual(code, 0, out)

    def test_semantic_failures(self):
        self.cli("new", "feature", "checkout", "--risk", "low", "--scope", "ui,personal-data,infra,ai")
        broken = {
            "discovery.md": FILLED["discovery.md"].replace("Decision: go", "Decision: no-go")
                            .replace("| One-page checkout | merge steps | high | medium | medium |\n", ""),
            "ux.md": FILLED["ux.md"].replace("| n/a |", "| |").replace("[x]", "[ ]"),
            "data.md": FILLED["data.md"].replace("| contract |", "| |"),
            "cost.md": FILLED["cost.md"].replace("(production): 25 USD", "(production): TBD").replace("| 25 USD |", "| TBD |"),
            "ai-risk.md": FILLED["ai-risk.md"].replace("| 0.93 |", "| |"),
            "outcome.md": FILLED["outcome.md"].replace("mobile checkout conversion", "revenue"),
        }
        for name, text in broken.items():
            (self.change_dir() / name).write_text(text)
        self.set_phase("done")
        code, out = self.cli("check")
        self.assertEqual(code, 1)
        for fragment in ["compare at least two options", "decision is no-go",
                         "does not define states ['empty']", "accessibility checklist has unchecked items",
                         "privacy question 'purpose and lawful basis' is unanswered",
                         "'Total monthly (production):' needs an amount", "has no numeric monthly cost",
                         "eval 'faithfulness' has no result before review",
                         "success metric 'mobile checkout conversion' from discovery.md is not reported"]:
            self.assertIn(fragment, out)

    def test_retirement_type(self):
        self.new_change(change_type="retirement", risk="low", slug="api-v1")
        (self.change_dir() / "retirement.md").write_text(FILLED["retirement.md"].replace("2027-01-15", "next year"))
        self.set_phase("plan")
        code, out = self.cli("check")
        self.assertIn("sunset date must be YYYY-MM-DD", out)
        (self.change_dir() / "retirement.md").write_text(FILLED["retirement.md"])
        self.assertEqual(self.cli("check")[0], 0)


class StandardProfileLifecycleTests(HarnessCase):
    def test_feature_medium_requires_approved_discovery(self):
        self.set_roster(product_owner=["pat"])
        cid = self.new_change(risk="medium")
        self.assertIn('phase = "discover"', (self.change_dir() / "change.toml").read_text())
        (self.change_dir() / "discovery.md").write_text(FILLED["discovery.md"])
        code, out = self.cli("phase", cid, "spec")
        self.assertIn("discovery.md: requires approval", out)
        self.cli("approve", cid, "discovery.md", "--as", "pat", "--role", "product-owner")
        self.advance(cid, "spec")


if __name__ == "__main__":
    unittest.main()
