# Playbook: the harness, phase by phase and role by role

*Español: [Manual paso a paso](../es/manual.md).*

This is the long, literal version: for every phase, who acts, the exact command they run, why the harness asks for
it, what the failure looks like (real output, copied from a run) and how to get out of it. If you want the short
version first, read the [walkthrough](walkthrough.md). If you want the finished artifacts this page talks about,
they are in the [example change record](../examples/README.md).

Everything below follows one real change: **`2026-09-17-staff-csv-export`**, a small feature (studio staff can
export their bookings to CSV) of type `feature`, risk `medium`, scopes `ui,api`, in the `standard` profile.

## 0. Three rules that explain everything else

**The agent produces evidence, humans approve it, the platform proves the approval.** An agent may write every
document and run every check. It may never run `sdlc approve` or `sdlc amend`, never edit `approvals.toml` or
`audit.jsonl`. If it does, CI catches it, because the approval is verified against GitHub or GitLab, not against
the file.

**`sdlc check` and `sdlc phase` do different things, and this confuses everyone once.** A rule makes an artifact
mandatory *once the change has moved past that artifact's phase*. While your change sits in `discover`,
`sdlc check` says `OK: 0 errors` even if `discovery.md` is still full of placeholders. The gate fires when you try
to leave: `sdlc phase <id> spec` evaluates the rules for the phase you are entering. Use `sdlc status` when you want
the forward-looking answer — it tells you what blocks the *next* phase, before you try.

**A receipt is bound to the bytes of the file.** Approving records the SHA-256 of the artifact. Change one character
afterwards and the approval is stale. That is not bureaucracy: it is what stops "approved" from drifting away from
what was actually read.

## 1. The cast

One person can hold several roles; a role can be a platform team (`@acme/security`). Who may approve what lives in
`[authority]` in `.harness/roster.toml`, and **an artifact only needs a receipt if the profile says so**.

| Role | Approves (when the profile requires it) | In plain words |
|---|---|---|
| `product-owner` | `discovery.md`, `spec.md`, `ux.md`, `outcome.md` | decides the problem is worth solving and that "done" means the right thing |
| `tech-lead` | `spec.md`, `design.md`, `plan.md`, `verification.md`, `review.md`, `cost.md`, `retirement.md` | answers for the technical shape and for the evidence being real |
| `architect` | `design.md`, ADRs, `ai-risk.md`, `retirement.md`, deviations | answers for decisions that are hard to reverse |
| `security` | `threat-model.md`, `data.md`, `ai-risk.md`, deviations, exceptions | accepts, or refuses to accept, security risk |
| `ux-lead` | `ux.md` | answers for the states a user actually sees, including errors |
| `data-steward` | `data.md` | answers for the data and its lawful use |
| `finops` | `cost.md` | answers for the bill |
| `release-manager` | `release.md` | decides this version ships, and how it is rolled back |
| `sre` | `runbook.md` | answers for operating it at 3 a.m. |
| `platform` | (no artifact) | owns the harness install, CI and the roster |
| the agent | **nothing, ever** | writes documents and code, runs checks, asks for approvals |

In `standard`, the artifacts that need a receipt are `discovery.md`, `spec.md`, `design.md`, ADRs,
`threat-model.md`, `data.md`, `ai-risk.md`, `retirement.md` and `release.md`. In `lite`, none. In `regulated`,
nearly all of them, including `plan.md`, `verification.md`, `review.md`, `ux.md`, `cost.md` and `runbook.md`.

## 2. One-time setup — the platform role

```bash
pipx install git+https://github.com/huanrasan/sdlc-harness@v0.7.3
sdlc init path/to/repo --interactive          # asks profile, agents, CI, roster; --adopt for an existing repo
cd path/to/repo
python3 .harness/sdlc.pyz hooks               # pre-commit gates and commit-message check
python3 .harness/sdlc.pyz doctor              # configuration review
```

Then fill `.harness/roster.toml`. **A role with no members is a role nobody can approve for**, and the change will
stop dead at that gate:

```
WARN  roster: role 'product-owner' has no members (approves spec.md, discovery.md, ux.md, outcome.md)
```

Commit `.github/workflows/`, enable branch protection with the `harness` check required, and — if you are the only
maintainer — set `separation_of_duties = false` and turn on commit signing, per the
[upgrade notes](upgrading.md#if-you-are-the-only-maintainer-turn-on-commit-signing).

## 3. Phase by phase

Each phase below lists who acts, the command, and what actually goes wrong.

### `discover` — is this worth doing?

**Who:** the agent writes `discovery.md`; the `product-owner` approves it.

```bash
python3 .harness/sdlc.pyz new feature staff-csv-export --risk medium --scope ui,api   # agent
python3 .harness/sdlc.pyz status                                                      # anyone, anytime
```

`new` creates `docs/changes/<date>-<slug>/` with `change.toml` and a template per artifact. `status` immediately
tells you where you stand:

```
2026-09-18-staff-csv-export  [feature risk=medium scopes=ui,api]  phase: discover -> spec
  - blocks spec: docs/changes/2026-09-18-staff-csv-export/discovery.md: unfilled sections (<!-- sdlc:fill -->)
  next: fix the evidence listed above, then: python3 .harness/sdlc.pyz phase 2026-09-18-staff-csv-export spec
```

`discovery.md` must state the problem with evidence, at least two options **including doing nothing**, measurable
success metrics, and a decision. The decision is checked:

```
ERROR docs/changes/<id>/discovery.md: 'Decision:' must be one of go, no-go, iterate
```

Write `go`, `no-go` or `iterate` literally. `no-go` is a valid outcome and stops the change there — that is a
success, not a failure.

**The approval (product-owner, at their own terminal):**

```bash
python3 .harness/sdlc.pyz approve <id> discovery.md --as pat --role product-owner
```

Two things that go wrong the first time:

```
ERROR role 'security' is not authorized to approve 'spec.md' (allowed: ['product-owner', 'tech-lead'])
ERROR 'bob' is not a member of role 'product-owner' in .harness/roster.toml
```

The first means the artifact's `[authority]` entry does not list your role; the second means your username is not in
the roster. Both are fixed in `.harness/roster.toml`, by the platform role, not by editing the receipt.

When it works you get the receipt and an instruction that matters:

```
receipt recorded: docs/changes/<id>/discovery.md sha256=ae6b3a077a91 approver=pat role=product-owner
Commit approvals.toml and audit.jsonl, then approve the pull request on the platform.
```

**Do not skip that second sentence.** The local receipt is half the proof; CI also asks GitHub or GitLab whether
that person really approved. If you forget, CI says:

```
ERROR <artifact> (pat): no current approval from 'pat' on the pull/merge request
```

### `spec` — what does "done" mean?

**Who:** agent writes; `product-owner` or `tech-lead` approves.

```bash
python3 .harness/sdlc.pyz phase <id> spec     # agent, after discovery.md is approved
```

If you try to advance before the approval exists:

```
gate blocked: <id> stays in 'discover'. Run `python3 .harness/sdlc.pyz status --change <id>` for what is missing and who approves.
ERROR docs/changes/<id>/discovery.md: requires approval by one of roles ['product-owner']; a human approves with:
      python3 .harness/sdlc.pyz approve <id> discovery.md --as <username> --role product-owner
```

The error carries the command. Hand that line to the person who holds the role.

`spec.md` needs acceptance criteria written `AC-1`, `AC-2`, … in Given/When/Then form, **each naming the test that
will verify it**, plus non-functional requirements with numbers ("p95 < 300 ms", not "fast"). Naming the test here
is what makes the `plan` and `verify` gates pass later without inventing links.

Phases advance one at a time. This is deliberate:

```
ERROR cannot skip phases: discover -> design
```

### `design` — how, and what can go wrong

**Who:** agent writes `design.md` (and `ux.md` because this change declares scope `ui`); `tech-lead` or `architect`
approves the design. In `standard`, `ux.md` does **not** need a receipt; in `regulated` it does.

```bash
python3 .harness/sdlc.pyz phase <id> design
```

`design.md` covers the solution, failure modes, observability, rollout and rollback. A new service, datastore,
boundary or public contract also needs an ADR under `docs/adr/`, approved by the `architect`. `ux.md` lists the four
states of every screen (empty, loading, error, success) and a completed WCAG 2.2 AA checklist — "n/a: reason" is an
acceptable answer, silence is not.

Typical block:

```
ERROR docs/changes/<id>/design.md: requires approval by one of roles ['tech-lead', 'architect']; a human approves with:
      python3 .harness/sdlc.pyz approve <id> design.md --as <username> --role tech-lead
ERROR docs/changes/<id>/ux.md: 'Booking list' does not define states ['empty'] (write 'n/a' if not applicable)
```

### `plan` — every criterion traced to a test

**Who:** agent. Receipt only in `regulated`.

`plan.md` has a traceability table (each `AC-n` and each threat `T-n` to the tests that cover it) and tasks whose
"done when" is a command, not an opinion. The gate reads `spec.md` and compares:

```
ERROR docs/changes/<id>/plan.md: AC-3 from spec.md is missing in the traceability table
ERROR docs/changes/<id>/plan.md: AC-2 has no planned test
```

Fix it by adding the row, not by deleting the criterion from `spec.md` — though if the criterion genuinely should
not exist, remove it there and re-approve the spec.

### `implement` — code, in small commits

**Who:** agent, with the human reviewing as usual.

Two sensors watch git history here, and they only run with a base ref (which is what CI passes):

```bash
python3 .harness/sdlc.pyz check --base origin/main
```

```
ERROR test-first: commit 4f2a9c1b23 'feat: export bookings' changes source before any test change
      (add tests first or a 'TDD-Waiver: <reason>' trailer)
ERROR weakened test: tests/test_export.py: added python skip/xfail: @pytest.mark.skip(reason="flaky")
      (fix the test or add a 'Test-Waiver: <reason>' trailer)
```

The escape hatch is a commit trailer written by a human, with a reason. Before trusting the configuration, check
what the sensor is even looking at — files outside your globs are invisible to it:

```bash
python3 .harness/sdlc.pyz tdd --explain                          # every tracked file, nothing hidden
python3 .harness/sdlc.pyz tdd --explain src/proxy.ts src/a.test.ts   # just these, and which rule decided
```

```
src/proxy.ts: source - matches source glob `src/**/*.ts`
README.md: other - matches no test glob and no source glob
```

### `verify` — evidence, not assertions

**Who:** agent runs everything and records it; `tech-lead` approves in `regulated`.

`verification.md` records the commands and their real output, one row per acceptance criterion, and the scanner
findings with their disposition. In the evidence column, anything in `backticks` is checked, so write it as one of
three things:

| Form | Example | What the gate does |
|---|---|---|
| a test name — a sentence is fine | `` `returns 200 with db ok in under 500 ms` `` | checks it exists under `verification.test_paths` |
| a repository path | `` `src/export.ts` ``, `` `tests/test_x.py::test_y` ``, `` `src/a.ts:12` `` | checks the file exists |
| a command, marked with `$ ` | `` `$ pnpm test:integration` `` | nothing: a command is as unverifiable as prose |

Anything else fails, and that is deliberate — it is how evidence pointing at nothing gets caught:

```
ERROR docs/changes/<id>/verification.md: AC-2 cites `sdlc tdd --explain`, which is not a test under
      verification.test_paths nor a file in the repository (write a command as `$ sdlc tdd --explain` if that is what it is)
ERROR docs/changes/<id>/verification.md: AC-4 cites `src/components/OldBanner.tsx`, which does not exist in the repository
```

Mark the command, fix the path. **Do not drop the backticks to get past the gate**: prose passes because it cannot be
checked, which makes the evidence worse, not better.

The result must be `pass`, `verified` or `n/a`:

```
ERROR docs/changes/<id>/verification.md: AC-1 result is 'fail' (expected pass/verified/n/a, or blocked/pending with an owner and a reason)
```

**When something honestly cannot be verified yet** — you need an admin permission, an environment that does not
exist — say so instead of inventing a result:

```
| AC-9 | blocked | blocked - owner: rita - needs repository admin to protect the branch |
```

Without an owner the gate refuses the excuse:

```
ERROR docs/changes/<id>/verification.md: AC-1 is 'blocked' and must name an owner and a reason,
      e.g. 'blocked - owner: rita - needs repository admin to protect the branch'
```

With one, the record is accepted as truthful and the phase still does not advance, which is the point:

```
ERROR docs/changes/<id>/verification.md: AC-1 is blocked (owner: rita); verify cannot close until it passes,
      or record it as n/a with the reason
```

Evidence from scanners is policy, not vibes:

```bash
python3 .harness/sdlc.pyz evidence check
```

```
ERROR missing evidence 'sast': expected sdlc-evidence/sast*.sarif
ERROR trivy: high CVE-2026-1234 at package-lock.json: lodash 4.17.20 is vulnerable to prototype pollution
```

If you cannot fix a finding now, do not edit the file — propose an exception with an expiry, which a security role
must approve:

```bash
python3 .harness/sdlc.pyz exception propose "CVE-2026-1234" "package-lock.json" --reason "upstream fix in 4.17.22, tracked in ISSUE-88" --days 30   # agent
python3 .harness/sdlc.pyz exception approve "CVE-2026-1234" "package-lock.json" --as sam --role security             # human
```

Until it is approved it suppresses nothing, and `sdlc check` keeps saying so.

### `review` — a second pair of eyes that did not write the code

**Who:** a *fresh-context* reviewer (a second agent session, or a person); `tech-lead` approves in `regulated`.

The reviewer must not be the session that implemented the change — the whole value is that it has not convinced
itself already. In the example, this is where a real authorization bug was found: the permission check ran after the
query was built. `review.md` records the verdict, findings by severity, and **what was not reviewed**.

### `release` — version, digests, rollback

**Who:** agent prepares `release.md`; `release-manager` approves; CI does the rest on a tag.

```bash
git tag v1.4.0 && git push origin v1.4.0
```

The pipeline runs the gates on the tagged commit, your `scripts/build-release` (executable, no arguments,
everything to publish in `dist/`), a CycloneDX SBOM checked against the licence policy, SLSA provenance, SBOM
attestation and keyless Sigstore signatures.

**The trap everyone falls into:** the digests only exist after the build, but `release.md` was approved before. Do
not leave them out to protect the receipt — add them and let the approver see exactly what changed:

```bash
python3 .harness/sdlc.pyz amend <id> release.md --as rita --role release-manager
```

It prints the diff since the approval and asks for a typed `yes`. It refuses to run without a terminal, so an agent
cannot use it:

```
ERROR amend must be run by a human at a terminal; an agent cannot confirm an approval
```

### `operate` and `done` — did it work?

**Who:** agent measures; `product-owner` approves `outcome.md` where the profile requires it; `sre` owns
`runbook.md` when the change declares `infra`.

`outcome.md` compares the metrics promised in `discovery.md` against what actually happened, and ends in `keep`,
`iterate`, `rollback` or `retire`. The gate checks every promised metric is reported:

```
ERROR docs/changes/<id>/outcome.md: success metric 'exports per week' from discovery.md is not reported
```

A metric that missed its target is not a failure of the process. The example ends in `iterate`, honestly.

## 4. Role cards

**If you are the `product-owner`:** you will be asked to approve `discovery.md` (is this worth doing), `spec.md`
(does "done" mean the right thing) and, at the end, `outcome.md`. Your entire command set is
`sdlc approve <id> <artifact> --as <you> --role product-owner`, plus an approving review on the pull request. If the
document changed after you approved it, use `sdlc amend` instead and read the diff.

**If you are the `tech-lead`:** `spec.md`, `design.md` and, in `regulated`, `plan.md`, `verification.md` and
`review.md`. Your real job at the `verification.md` gate is to check that the evidence is real: the tests named in
the table exist, and the commands pasted actually produce that output.

**If you are the `architect`:** ADRs and `design.md` for anything hard to reverse. You also approve deviations from
organization policy: `sdlc deviation approve <policy-key> --as <you> --role architect`.

**If you are `security`:** `threat-model.md`, `data.md`, `ai-risk.md`, and every exception to a scanner finding.
Each exception you approve has an expiry, and when it expires the gate goes red again — which is the design.

**If you are the `release-manager`:** `release.md`, and you are the person who says a version ships. Check the
rollback procedure was tested, not just written.

**If you are `platform`:** you own `sdlc init`, `sdlc upgrade`, the roster, CODEOWNERS (`sdlc codeowners --check` in
CI) and the CI configuration. You do not approve artifacts; you make it possible for others to.

**If you are the agent:** you write documents and code, run `sdlc check`, `sdlc status`, `sdlc tdd --explain` and
`sdlc explain`, advance with `sdlc phase`, and propose deviations and exceptions. You stop and ask for every
approval. You never write in `approvals.toml`.

## 5. When you are stuck

The fastest route is to paste the error back into the harness:

```bash
python3 .harness/sdlc.pyz explain "approval by pat is stale (content changed); re-approve"
```

```
message: approval by pat is stale (content changed); re-approve
  cause: The artifact changed after it was approved, so the receipt no longer matches.
  fix: The approver reads the delta and confirms it in one step: python3 .harness/sdlc.pyz amend
       <id> <artifact> --as <user> --role <role>. Never drop true information from a document to
       protect its receipt.
```

`explain` also answers `sdlc explain design`, `sdlc explain spec.md`, `sdlc explain security`,
`sdlc explain receipt` and `sdlc explain separation-of-duties`. The full message catalogue is in the
[walkthrough](walkthrough.md#7-when-a-gate-blocks), and the vocabulary is in the [glossary](glossary.md).

## 6. Three situations that are not failures

| Situation | What to do | What **not** to do |
|---|---|---|
| A criterion cannot be verified yet | `blocked - owner: <who> - <what has to happen>` in `verification.md` | write `pass`, or `n/a` for something merely undone |
| An approved document needs a true addition | `sdlc amend`, approver reads the diff | leave the information out to protect the receipt |
| A finding or a policy cannot be met now | `sdlc exception propose` / `sdlc deviation propose`, with expiry, then a human approves | write the risk in prose where nothing makes it expire |
