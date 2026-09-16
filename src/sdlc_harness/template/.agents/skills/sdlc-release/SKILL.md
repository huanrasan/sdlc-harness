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
4. Deployment strategy proportional to risk: feature flag, canary or blue/green for medium/high risk;
   define health signals and automatic rollback thresholds.
5. Data and infrastructure: confirm migrations are backward compatible (expand/contract) and that the
   rollback path was tested in a non-production environment.
6. Fill `release.md`: scope, version, artifacts and digests, rollout plan, success metrics, rollback trigger
   and procedure, communication plan. The release manager approves `release.md` with a receipt.
7. Production deploys are executed or approved by a human through the pipeline's environment protection.

After release, hand over to `sdlc-operate` for the post-release check.
