# renovate-config

Shared Renovate baseline preset for all kepler repositories
(orgs: `fits-ki`, `Sternwarte-Hof`, `Feigel-IT-Services`, `Schachfreunde-Bad-Steben`).

## Usage

Every repository keeps a minimal `renovate.json` that extends this preset and only
carries project-specific settings (groups, ignorePaths, constraints, dedicated
approval rules, deliberate overrides):

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>fits-ki/renovate-config"],
  "ignorePaths": ["..."],
  "packageRules": ["..."]
}
```

Renovate resolves `github>fits-ki/renovate-config` to `default.json` on this repo's
default branch (`main`). Changes to the preset therefore go through
`develop` -> release PR -> `main`, like any release. A merged preset change affects
all consuming repositories on their next Renovate run.

## Baseline contract

- All dependency PRs target `develop` only (`baseBranchPatterns`).
- Routine updates run Mondays 00:00-08:00 Europe/Berlin; `updateNotScheduled: false`
  blocks routine branch updates outside the window.
- `automerge: false` everywhere — the top-level `false` is inherited by every
  rule, with an explicit `automerge: false` additionally set on the
  major-update rule and on vulnerability alerts — so every merge is a
  manual, reviewed decision.
- `ignoreTests: false` keeps CI signal on dependency updates.
- `minimumReleaseAge: 7 days` and `internalChecksFilter: strict` hold back
  freshly published releases (supply-chain margin; with the weekly cadence the
  extra delay is negligible).
- `platformAutomerge: false`, `ignoreUnstable: true` (explicit), `ignoreScripts`
  and `ignorePlugins` (no install-time scripts/plugins during updates),
  `semanticCommits` for conventional-commit PR titles, `pinDigests: true`
  globally (Docker images and GitHub Actions pinned to digests),
  `postUpdateOptions: pnpmDedupe` for pnpm lockfile hygiene.
- Extended presets: `:separateMultipleMajorReleases` (one PR per major version)
  and `group:react` (react/react-dom batched where present).
- Rate limits: `prHourlyLimit: 2`, `prConcurrentLimit: 3`, `branchConcurrentLimit: 3`.
- `dependencyDashboard: true` — the dashboard issue is the control surface for
  pending and approval-gated updates.
- `osvVulnerabilityAlerts: true` adds the OSV feed next to GitHub's advisory data.
- `pinDigests: true` pins actions and Docker references to digests; keep
  `# vX.Y.Z` version comments on pinned GitHub Actions.
- Lockfile maintenance runs weekly in the same Monday window.
- PR labels: `dependencies` on all PRs, `dependencies` + `security` on
  vulnerability PRs.

### Manual pilot — no automerge profile is active

There is deliberately **no** active automerge opt-in profile yet. A future
opt-in for a repository requires all of: verified branch protection on
`develop`, a required merge-gate check that stays green, two successful
routine cycles proving CI reliability, resolved local grouping/approval
rules, and an explicit opt-in in that repository. Until then every merge
stays manual.

### Preset release flow

`develop` -> `main` remains a separately approved release step; nothing here
changes deployments, tariffs or repository protection settings.

### Package rules in the preset

1. **Major updates** require manual approval in the Dependency Dashboard
   (`dependencyDashboardApproval`).
2. **CI and infrastructure batch**: compatible (non-major) updates from
   `github-actions`, `dockerfile`, `docker-compose` and `devcontainer` managers are
   grouped into one `CI and infrastructure` PR, excluding anything disabled,
   approval-gated or vulnerability-driven.

## Vulnerability updates — exceptions to every gate

Security updates bypass all routine gates by design: they run at any time, with no
minimum release age, no grouping, no dashboard approval, no PR/branch limits —
and still no automerge. **After a critical security PR lands on `develop`, ship it
to `main` through the hotfix/release path instead of waiting for the next regular
release.**

## What stays in each repository

- `ignorePaths` (project layout differs).
- Project-specific `packageRules`: dependency batches
  (`Application dependencies`, `Website dependencies`, ...), tool families
  (Laravel, Electron, Tailwind, Astro, ...), dedicated approval rules
  (runtime upgrades, pinned provenance artifacts, tool constraints) and their
  JSONata guards.
- `constraints`, `customManagers`, `customDatasources`, `rangeStrategy` and other
  manager-level settings.
- Deliberate baseline overrides (e.g. a longer `minimumReleaseAge`, tighter
  concurrent limits).

## Changing the preset

1. Branch from `develop`, open a PR against `develop`.
2. Release to `main` like any release.
3. The next Renovate run in every consuming repo picks the new baseline up;
   verify against one repo's dry run / dependency dashboard before assuming a
   fleet-wide effect.

### Validation

CI runs the Python baseline tests plus the actual repository-preset validator:

```sh
python3 -m unittest discover -s tests -v
npx --yes --ignore-scripts --package=renovate@44.176.2 --call '
  set -eu
  RENOVATE_VALIDATOR="$(command -v renovate-config-validator)"
  export RENOVATE_VALIDATOR
  node --test tests/validation.test.mjs
  node scripts/validate-preset.mjs "$RENOVATE_VALIDATOR" default.json
'
```

The helper first runs `--strict --no-global` so global-only options are
rejected. It then uses the **same pinned Renovate installation** to recursively
resolve `extends`, validate the resulting repository configuration and reject
inherited automerge activation. An unresolved preset is a failure, not a
warning to ignore. The Node regression tests exercise this actual helper with
valid and invalid temporary configurations; the real baseline remains unchanged.

A plain `renovate-config-validator --strict default.json` is insufficient:
explicit filenames default to global-config validation, and the CLI does not
resolve top-level `extends`. The helper uses Renovate's internal resolver API;
tool upgrades must pass the same regression tests before merging.
