"""`sdlc explain <topic>`: the documentation where the work happens - phases, artifacts, roles and error messages.

Topics are matched loosely, so pasting a gate message works: `sdlc explain "approval by alice is stale"`.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from . import authority
from .core import PHASES, VENDORED_CLI, TYPES, SCOPES

DOCS = "https://github.com/huanrasan/sdlc-harness/blob/main/docs/en/walkthrough.md"

PHASE_DOC = {
    "discover": ("Is it worth building?", "discovery.md", "sdlc-discover",
                 "Problem with evidence, target users, value hypothesis, success metrics with baseline and target, "
                 "at least two options including 'do nothing', and Decision: go | no-go | iterate."),
    "spec": ("What does done mean?", "spec.md", "sdlc-specify",
             "Acceptance criteria AC-n as Given/When/Then and non-functional requirements with numbers. "
             "Every criterion must be verifiable by a test or a named manual check."),
    "design": ("How will we build it, and what could go wrong?", "design.md, ADRs, threat-model.md + scope artifacts",
               "sdlc-design (+ sdlc-ux, sdlc-data, sdlc-finops, sdlc-ai-risk, sdlc-retire)",
               "Solution, interfaces, data, failure modes, rollout and rollback; an ADR per significant decision; "
               "threats with verifiable controls; UX, data/privacy, cost and AI-risk artifacts by scope."),
    "plan": ("In what order, and how will we know each step is done?", "plan.md", "sdlc-plan",
             "Every AC-n and T-n traced to a planned test, tasks with a 'done when' command, rollback per migration."),
    "implement": ("Write it, test first.", "code and tests", "sdlc-implement",
                  "Test before or with the code (test-first sensor), small commits, no weakened tests, "
                  "respect layer rules and contract compatibility."),
    "verify": ("Prove it works.", "verification.md + sdlc-evidence/", "sdlc-verify",
               "Commands and their output, every AC-n with result and evidence, scanner findings with a disposition."),
    "review": ("Would someone else accept this?", "review.md", "sdlc-review",
               "Independent review from a fresh context; verdict ready-for-human-approval, checklist complete."),
    "release": ("Ship it safely.", "release.md (+ runbook.md)", "sdlc-release",
                "Version, artifact digests, SBOM, provenance and signatures, rollout plan, tested rollback."),
    "operate": ("Did it work?", "outcome.md, runbook.md", "sdlc-operate, sdlc-outcome",
                "Telemetry and runbook in place; every success metric measured and a keep/iterate/rollback/retire decision."),
    "done": ("Closed.", "-", "sdlc-maintain",
             "Nothing pending. Lessons worth keeping go to memory (`sdlc memory add`)."),
}

ARTIFACT_DOC = {
    "discovery.md": "Opportunity framing: problem, users, hypothesis, success metrics, options, go/no-go decision.",
    "spec.md": "What 'done' means: acceptance criteria AC-n and non-functional requirements with numbers.",
    "design.md": "Technical design: components, interfaces, data, failure modes, observability, rollout and rollback.",
    "adr": "Architecture decision record: context, weighted criteria, at least two options, decision, consequences.",
    "threat-model.md": "Threats T-n per trust boundary (STRIDE, OWASP LLM/Agentic) with verifiable controls.",
    "ux.md": "User flows, screen states (empty, loading, error, success), WCAG 2.2 AA checklist, validation.",
    "data.md": "Data changes with classification and owner, migrations, rollback, retention; privacy impact.",
    "cost.md": "Cost estimate with pricing drivers, monthly totals, unit economics and budget guardrails.",
    "ai-risk.md": "AI use case, risk classification, risks with mitigations, evaluations with thresholds, oversight.",
    "retirement.md": "Consumer inventory, deprecation timeline and sunset date, data disposition, teardown, rollback.",
    "plan.md": "Traceability of criteria and threats to tests, ordered tasks with 'done when' checks.",
    "verification.md": "Evidence: commands run, result per criterion, scanner findings and their disposition.",
    "review.md": "Independent review: verdict, findings by severity, checklist, what was not reviewed.",
    "release.md": "Release record: version, artifacts and digests, rollout, success metrics, rollback, approver.",
    "runbook.md": "How to operate it: dashboards, alerts and their meaning, diagnostics, safe mitigations.",
    "outcome.md": "Measured results against the discovery metrics and a keep/iterate/rollback/retire decision.",
}

ERROR_DOC = [
    (r"required after phase", "The artifact does not exist yet.",
     "Copy it from docs/sdlc/templates/ into the change folder and fill it in."),
    (r"unfilled sections", "Template placeholders are still there.",
     "Complete each marked section, or write 'n/a: reason' where it does not apply."),
    (r"missing in the traceability table|has no planned test", "A criterion or threat is not traced to a test.",
     "Add the row in plan.md with the test that will cover it."),
    (r"has no verification result|result is", "verification.md does not show a passing result for a criterion.",
     "Run the test, record the real result and evidence. Never edit a failure into a pass."),
    (r"requires approval by one of roles", "A human gate is pending.",
     f"A person holding that role runs: python3 {VENDORED_CLI} approve <id> <artifact> --as <user> --role <role>"),
    (r"is stale \(content changed\)|approval was given on different content",
     "The artifact changed after it was approved, so the receipt no longer matches.",
     f"The approver reads the delta and confirms it in one step: python3 {VENDORED_CLI} amend <id> <artifact> "
     f"--as <user> --role <role>. Never drop true information from a document to protect its receipt."),
    (r"no current approval from", "There is a receipt in the repository but nobody approved on the platform.",
     "Approve the pull request with the same account named in the receipt."),
    (r"receipt was added after the approval", "The receipt was committed after the platform review.",
     "Commit and push the receipt first, then submit the approving review."),
    (r"separation of duties", "The approver also authored the change.",
     "Have another role holder approve, or set separation_of_duties = false in .harness/roster.toml for solo work."),
    (r"must have a signature the platform verifies",
     "With separation_of_duties = false the receipt stands in for a platform review, so it must arrive in a signed "
     "commit: otherwise it is only a file the author wrote.",
     "Enable commit signing (git config commit.gpgsign true; register the key or your SSH signing key on the "
     "platform), then amend the commit that adds approvals.toml."),
    (r"is '(blocked|pending)'|is (blocked|pending) \(owner",
     "A criterion is honestly not verified yet. The record is valid, but verify does not close.",
     "Finish the check and record the real result, or record it as n/a with the reason if it no longer applies."),
    (r"must name an owner and a reason",
     "A blocked or pending criterion without an owner is an excuse, not a record.",
     "Write it as: blocked - owner: <person> - <what has to happen>."),
    (r"is proposed and awaits approval",
     "A deviation or exception was proposed but nobody has approved it.",
     f"A role holder confirms it: python3 {VENDORED_CLI} <deviation|exception> approve <key> --as <user> "
     f"--role <role>. Until then it does not suppress anything."),
    (r"Guardrails does not cover",
     "The cost guardrails section does not state all four controls.",
     "Give the monthly budget, the alert thresholds, the cost allocation tags and what is shut down when idle."),
    (r"needs an amount",
     "The production total has no number on that line.",
     "Write it with the currency before or after: 'Total monthly (production): USD 77.40'."),
    (r"test-first", "A behaviour commit changed source before any test change in this range.",
     "Reorder commits so the test comes first, or add a human-written 'TDD-Waiver: <reason>' trailer."),
    (r"weakened test", "A test was skipped, focused or deleted.",
     "Fix the test instead. A justified exception needs a 'Test-Waiver: <reason>' trailer."),
    (r"breaking change without major version bump", "An API contract lost backward compatibility.",
     "Keep compatibility, or raise the major of info.version and record the decision in an ADR."),
    (r"must not depend on|must not import", "An import breaks the layer rules in .harness/architecture.toml.",
     "Fix the dependency, or change the rule through a new ADR and update architecture.toml."),
    (r"missing evidence", "A required scanner did not produce evidence.",
     "Run it in CI writing SARIF to sdlc-evidence/<kind>.sarif (or a CycloneDX sbom*.json)."),
    (r"expired on", "A time-boxed exception or deviation ran out.",
     "Fix the finding, or renew the entry with a fresh expiry and an authorized approver."),
    (r"awaits a human approver", "A baseline exception has no approver yet.",
     "A security role holder reviews the finding and puts their username in .harness/exceptions.toml."),
    (r"skills index is stale|out of sync|drifted", "Generated files no longer match the skills.",
     f"python3 {VENDORED_CLI} sync"),
    (r"INDEX.md is stale", "A memory entry was added or edited by hand.",
     f"python3 {VENDORED_CLI} memory index"),
    (r"cannot skip phases", "Phases advance one at a time.",
     "Advance to the immediate next phase; the gate for each one must pass."),
    (r"organization requires|policy .*: ", "The project is below a mandatory organization minimum.",
     "Raise the setting, or register a deviation with reason, authorized approver and expiry in .harness/deviations.toml."),
    (r"hash chain broken|append-only", "The audit log was edited instead of appended to.",
     "Restore the file from git history; audit events are append-only and verified in CI."),
    (r"ai_assisted", "The AI-use disclosure field is missing or not a boolean.",
     "Set ai_assisted = true or false in change.toml."),
]


def _phase_text(name: str) -> str:
    question, artifacts, skill, detail = PHASE_DOC[name]
    idx = PHASES.index(name)
    prev = PHASES[idx - 1] if idx else "-"
    nxt = PHASES[idx + 1] if idx + 1 < len(PHASES) else "-"
    return "\n".join([
        f"phase '{name}': {question}",
        f"  previous: {prev}    next: {nxt}",
        f"  artifacts: {artifacts}",
        f"  skill: {skill}",
        f"  gate: {detail}",
        f"  advance with: python3 {VENDORED_CLI} phase <id> {nxt}" if nxt != "-" else "  the change is closed",
    ])


def _artifact_text(name: str, cfg: dict | None) -> str:
    lines = [f"artifact '{name}': {ARTIFACT_DOC[name]}"]
    if cfg:
        roles = authority.approver_roles(cfg, name)
        rules = [r for r in cfg["_profile"].get("rules", []) if r["artifact"] == name]
        if rules:
            needs = "yes" if any(r.get("approve") for r in rules) else "no (reviewed in the pull request)"
            when = "; ".join(f"{','.join(r.get('types', TYPES))} from risk {r.get('min_risk', 'low')}"
                             + (f" with scope {','.join(r['scopes'])}" if r.get("scopes") else "") for r in rules)
            lines += [f"  required in this profile for: {when}", f"  approval receipt required: {needs}"]
        else:
            lines.append("  not required by the active profile")
        if roles:
            members = sorted({m.lstrip("@") for role in roles for m in authority.roles(cfg).get(role, [])})
            lines.append(f"  approving roles: {', '.join(roles)} ({', '.join(members) or 'no members in the roster'})")
    if name != "adr":
        lines.append(f"  template: docs/sdlc/templates/{name}")
    return "\n".join(lines)


def _role_text(role: str, cfg: dict | None) -> str:
    lines = [f"role '{role}'"]
    if cfg:
        members = [m for m in authority.roles(cfg).get(role, [])]
        lines.append(f"  members: {', '.join(members) or 'none: add them to .harness/roster.toml'}")
        approves = [key for key, roles in cfg["_roster"].get("authority", {}).items() if role in roles]
        lines.append(f"  may approve: {', '.join(approves) or 'nothing'}")
    return "\n".join(lines)


def _wrap(label: str, text: str) -> str:
    """Wrapped so long explanations stay readable in a narrow terminal and in the recorded demo."""
    return textwrap.fill(text, width=96, initial_indent=f"  {label}: ", subsequent_indent=" " * (len(label) + 4))


def _error_text(query: str) -> str | None:
    for pattern, cause, fix in ERROR_DOC:
        if re.search(pattern, query, re.I):
            return "\n".join([f"message: {query.strip()}", _wrap("cause", cause), _wrap("fix", fix)])
    return None


def topics(cfg: dict | None) -> str:
    lines = ["Topics:", "  phases:    " + ", ".join(PHASES), "  artifacts: " + ", ".join(sorted(ARTIFACT_DOC))]
    if cfg:
        lines.append("  roles:     " + ", ".join(sorted(authority.roles(cfg))))
    lines += [
        "  concepts:  change-record, receipt, profile, scope, sensor, gate, evidence, memory, deviation, exception",
        "  scopes:    " + ", ".join(SCOPES),
        "",
        "Paste a gate message to get its cause and fix, for example:",
        '  sdlc explain "approval by alice is stale (content changed); re-approve"',
        f"Full documentation: {DOCS}",
    ]
    return "\n".join(lines)


CONCEPT_DOC = {
    "change-record": "A folder under docs/changes/<id>/ holding change.toml (type, risk, scopes, phase, AI disclosure) "
                     "and the artifacts for the phases completed so far. It is the system of record for the change.",
    "receipt": "An entry in approvals.toml with the SHA-256 of the approved artifact, the approver and their role. "
               "Editing the artifact invalidates it; CI verifies it against the platform review.",
    "profile": "lite | standard | regulated (or your own): decides which artifacts are mandatory per type, risk and "
               "scope, which need approval, sensor levels and required evidence. Set in harness.toml.",
    "scope": "A tag on a change (ui, api, data, personal-data, infra, ai) that switches conditional artifacts on.",
    "sensor": "A deterministic check after the fact: tests, linters, scanners, test-first and weakened-test history "
              "checks, layer rules, contract compatibility.",
    "gate": "The check that must pass before a change moves to the next phase: evidence present, internally "
            "consistent and, where the profile says so, approved by a human.",
    "evidence": "Scanner output in standard formats under sdlc-evidence/ (SARIF findings, CycloneDX SBOM) plus the "
                "artifacts in the change record.",
    "memory": "Curated Markdown entries in docs/memory/ (decisions, lessons, conventions, pitfalls) that agents search "
              "before starting work. Organization memory arrives with `sdlc org pull`.",
    "deviation": "A time-boxed, approved exception to a mandatory organization policy, in .harness/deviations.toml. "
                 "An agent may write the proposal (`sdlc deviation propose`), only a human approves it.",
    "exception": "A time-boxed, security-approved exception to a scanner finding or denied licence, in "
                 ".harness/exceptions.toml. Proposed with `sdlc exception propose`, approved by a human.",
    "amend": "Re-approving an artifact after reading the diff since the last approval (`sdlc amend`). It exists so "
             "that keeping a receipt valid is never a reason to leave true information out of a document.",
    "separation-of-duties": "The approver may not be the author. With one maintainer it is turned off in "
                            ".harness/roster.toml, and the platform review is replaced by a verified commit "
                            "signature: the receipt still binds to an identity the platform checked.",
}


def explain(query: str | None, cfg: dict | None, root: Path | None = None) -> int:
    if not query:
        print(topics(cfg))
        return 0
    key = query.strip().lower()
    if key in PHASE_DOC:
        print(_phase_text(key))
        return 0
    artifact = key if key in ARTIFACT_DOC else (f"{key}.md" if f"{key}.md" in ARTIFACT_DOC else None)
    if artifact:
        print(_artifact_text(artifact, cfg))
        return 0
    if key in CONCEPT_DOC:
        print(f"{key}: {CONCEPT_DOC[key]}")
        return 0
    if key in SCOPES:
        rules = [r for r in (cfg or {}).get("_profile", {}).get("rules", []) if key in r.get("scopes", [])]
        print(f"scope '{key}': adds {', '.join(sorted({r['artifact'] for r in rules})) or 'no extra artifacts'} "
              f"in the active profile")
        return 0
    if cfg and key in authority.roles(cfg):
        print(_role_text(key, cfg))
        return 0
    if text := _error_text(query):
        print(text)
        return 0
    print(f"No topic matches {query!r}.\n")
    print(topics(cfg))
    return 1
