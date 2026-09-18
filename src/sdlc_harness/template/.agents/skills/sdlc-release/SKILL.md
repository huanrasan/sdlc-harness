---
name: sdlc-release
description: Prepare a safe, traceable release - versioning, changelog, SBOM, signing/provenance, progressive rollout and rollback plan. Use in the release phase, before deploying, tagging a version or publishing an artifact.
license: MIT
metadata:
  harness-phase: release
---
# Release

## Steps

1. Confirm the change is merged with required approvals and all CI gates green. Do not release from a local build.
2. Determine the version with Semantic Versioning from Conventional Commits; update the changelog
   (Keep a Changelog format) with user-facing language.
3. Releases run through `.github/workflows/sdlc-release.yml` (or the GitLab `release-*` jobs): gates, build via
   `scripts/build-release`, CycloneDX SBOM with license policy, SLSA build provenance and SBOM attestations, and
   keyless Sigstore signatures. Record artifact digests, attestation and signature locations in `release.md`, plus
   the verification commands from the workflow header.
   The build contract, which the pipeline enforces: `scripts/build-release` is **executable**, takes **no
   arguments**, and leaves **every artifact to be published in `dist/`**. Provenance, signatures and the release
   itself are produced from `dist/*`, so anything left elsewhere is not signed and not published.
   Set `[release] sbom_source` in `harness.toml` to match what you actually ship: `dir:dist` inventories files,
   while a container release needs `docker-archive:dist/<image>.tar` (or `oci-archive:`). Scanning a saved image
   as a directory produces an SBOM of the tarball, not of the image, and the license policy then checks nothing.
4. Deployment strategy proportional to risk: feature flag, canary or blue/green for medium/high risk;
   define health signals and automatic rollback thresholds.
5. Data and infrastructure: confirm migrations are backward compatible (expand/contract) and that the
   rollback path was tested in a non-production environment.
6. Fill `release.md`: scope, version, artifacts and digests, rollout plan, success metrics, rollback trigger
   and procedure, communication plan. The release manager approves `release.md` with a receipt.
   Digests are known only after the build, so `release.md` is normally approved and then completed: add them and
   run `sdlc amend <change> release.md --as <approver> --role release-manager`, which shows the approver the diff
   and records a fresh receipt. Do not leave true information out of the document to protect a receipt.
7. Production deploys are executed or approved by a human through the pipeline's environment protection.

After release, hand over to `sdlc-operate` for the post-release check.
