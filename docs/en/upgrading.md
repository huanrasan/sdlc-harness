# Upgrade notes

*Español: [Notas de actualización](../es/actualizar.md).*

What changes for a repository that already runs the harness. Only releases with consequences for you appear here;
the full list of changes is in the [changelog](https://github.com/huanrasan/sdlc-harness/blob/main/CHANGELOG.md).

Upgrading is always the same two commands, and nothing is applied until you merge it:

```bash
pipx upgrade sdlc-harness && sdlc upgrade --dry-run   # review first
sdlc upgrade                                          # then apply
```

`sdlc upgrade` needs the templates, so run it from the installed package or from `sdlc-full.pyz`. The
`.harness/sdlc.pyz` inside your repository ships without them on purpose: it runs the gates, it does not install.

## 0.7.2 to 0.7.3

Nothing that passed before can fail now: the evidence check tries the old rule first. What changes is what you no
longer have to work around.

- **Put the backticks back.** If you rewrote evidence as prose because commands and paths in `backticks` failed the
  gate, restore them. Paths are now checked to exist; commands are accepted when marked `$ pnpm test`. Unmarked
  tokens that are neither a test nor a file still fail, with a message that says how to mark them.
- **`sdlc tdd --explain <path> ...`** answers for specific files and names the glob that decided each one. The full
  listing no longer truncates.
- **Spanish criteria no longer warn.** `Dado/Cuando/Entonces` and `debe` count as structured criteria.

## 0.6.x to 0.7.x

### Four things that can turn your pipeline red

**1. A new `workflows` job runs actionlint and zizmor.** The harness already required actions pinned by commit SHA
and no interpolation of untrusted context into `run:` blocks; this job is what verifies it. On an existing
repository it usually finds something the first time. The two most common findings are a `checkout` without
`persist-credentials: false` (the token stays in `.git/config` for every later step) and `${{ ... }}` inside a
`run:` block (a shell injection when the value comes from a pull request). Both are real. If you need to land the
upgrade before fixing them, delete the job from `.github/workflows/sdlc-gates.yml` and put it back when you are
ready, or keep it and mark what you cannot fix now with
`sdlc exception propose <rule> <path> --reason "..." --days 30`.

**2. Self-hosted runners need version 2.327.1 or newer.** The updated actions (`checkout` 7, `setup-python` 7,
`upload-artifact` 7, `download-artifact` 8, `dependency-review` 5) run on Node 24. GitHub-hosted runners already
satisfy this; a self-hosted fleet may not, and the failure message is about the runner, not about the harness.

**3. Your source globs may now match more files.** `tdd.source_globs` and `verification.test_paths` follow git
semantics: `**` spans any number of directories *including none*, and `*` stays inside one path segment. Before
0.7, `src/**/*.ts` silently missed `src/proxy.ts`, so files at the top of a directory were classified as `other`
and the test-first sensor ignored them. They are now covered, which is the point, but it means the sensor can start
reporting commits it used to let through. Run `sdlc tdd --explain` before you push: it prints how every tracked file
is classified and warns when code still falls outside the globs. If you wrote both `src/*.ts` and `src/**/*.ts` to
work around the old behaviour, the second pattern alone is now enough.

**4. Published signature bundles change format.** Releases are signed with `cosign sign-blob --new-bundle-format`,
which is the current Sigstore bundle. Anyone verifying with cosign 3 uses the recipe in the workflow header
unchanged; anyone still on cosign 2.x must add `--new-bundle-format` to `verify-blob`. Bundles published before the
upgrade are unaffected and still verify the old way, so tell consumers which release the format changes at.

### If you are the only maintainer, turn on commit signing

`separation_of_duties = false` was documented but unreachable: `sdlc approvals verify` demanded an approving review
from the person named in the receipt, and GitHub does not let you approve your own pull request. Every pull request
that added a receipt failed.

From 0.7, with separation of duties off, a commit signature the platform verifies replaces that review. The receipt
must arrive in a commit signed by the approver. Set it up once, before your next approval:

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then add that public key to GitHub under Settings → SSH and GPG keys as a **signing key**. An authentication key
with the same contents does not count; the API reports it separately and the check will keep failing. With more
than one person, leave `separation_of_duties = true`, which is still the default and still requires the review.

### What you gain

- **`sdlc amend <change> <artifact> --as <user> --role <role>`** shows the approver what changed since their
  approval and records a fresh receipt in one step. Use it instead of re-approving blind, and stop leaving true
  information out of an approved document to protect its receipt: add the release digests to `release.md` and
  amend.
- **`blocked` and `pending` results in `verification.md`**, when they name an owner and a reason, as in
  `blocked - owner: rita - needs repository admin to protect the branch`. The gate stays red and the phase does not
  advance, but the record no longer forces a choice between stalling and writing something untrue.
- **`sdlc deviation propose` and `sdlc exception propose`** let an agent record accepted risk with an expiry, in a
  pending state that suppresses nothing until a human with an authorized role runs the matching `approve`. Risk that
  used to end up as a paragraph in a document now expires on its own.
- **`sdlc check --staged`**, used by the pre-commit hook, validates only the change records the commit touches.
- **`[release] sbom_source` in `harness.toml`** decides what Syft scans. `dir:dist` inventories files; a container
  release needs `docker-archive:dist/<image>.tar`. Scanning a saved image as a directory produces an SBOM of the
  tarball, and the licence policy then checks nothing.
- **`sdlc status` and `sdlc explain`** (from 0.6) say what blocks each change and what any gate message means.
  `sdlc explain "<the error you got>"` is usually faster than reading the docs.

### Nothing to do

Approval receipts, audit logs, change records and profiles are unchanged. `sdlc upgrade` keeps every file you
customized and writes `<file>.sdlc-new` next to the ones where both you and the release changed the same file.
