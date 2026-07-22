[简体中文](CHANGELOG.zh-CN.md)

# Changelog

This project follows Semantic Versioning. Notable changes are recorded here.

## 0.6.1 - 2026-07-22

- Narrowed plain `doctor` to managed-file verification plus `codex --version`, avoiding the broader Codex diagnostic that inspects authentication and local state metadata.
- Documented `doctor --smoke` as an explicit authenticated, usage-consuming opt-in while keeping role and model identity unverified.
- Added a deterministic Skills-only submission packager that rejects MCP/app fields and excludes directory-unsupported screenshot metadata and files.
- Updated the Plugins Directory candidate materials, field limits, eight review cases, and package verification guidance without creating or submitting a portal draft.

## 0.6.0 - 2026-07-21

- Added directory-safe core mode, optional six-role enhanced mode, and fail-closed degraded handling without changing the local config/state schema.
- Added the read-only `status --format text|json` interface with stable schema version 1 and explicit unverified identity fields.
- Added a static bilingual GitHub Pages site, community health files, support/legal pages, issue templates, promotion assets, and an A/B evaluation protocol without telemetry or fixed savings claims.
- Expanded the manifest with public publisher, repository, website, legal, starter-prompt, and PNG screenshot metadata.
- Reworked the first-run documentation around the recommended inherited enhancement, three risk-level examples, explicit stop/removal controls, and cross-device guidance.
- Validated the core and enhanced lifecycle through a real local marketplace install, reinstall, upgrade, removal, and cross-platform CI.
- Prepared—but did not submit—the skills-only Plugins Directory package with five positive and three negative review cases.

## 0.5.1 - 2026-07-13

- Added self-contained light, dark, and composer SVG brand assets to make Model Economy easier to identify in Codex plugin settings and the composer.
- Used a flat geometric routing mark with no gradients, external fonts, scripts, or embedded raster content.
- Added manifest and asset-contract tests so future releases cannot silently lose or externalize the plugin artwork.

## 0.5.0 - 2026-07-13

- Added three on-demand lightweight leaf skills: `domain-context`, `module-design`, and `disposable-prototype`.
- Kept leaf skills at zero subagent starts with no task-classification, model-routing, or commit authority; production implementation remains under Model Economy's single orchestration authority.
- Added isolation and explicit bans on real accounts, external writes, destructive side effects, and all credential sources for disposable prototypes.
- Encoded lightweight triggers and outputs in the machine routing policy while keeping the six roles and `strong` limits unchanged.
- Allowed the exact GitHub service identity `noreply@github.com` in sensitive-content scans to avoid false positives on synthetic PR merge commits while continuing to reject other domain addresses and spoofed suffixes.

## 0.4.0 - 2026-07-11

- Replaced runtime dependencies on Superpowers skills with risk-triggered intent, planning, testing, and evidence gates.
- Clarified that installing or enabling Superpowers does not authorize its full workflow; only an explicit strict request for the current task hands off orchestration.
- Stopped requiring design documents or durable plans for simple work, kept short plans for standard work, and scaled testing to behavioral risk.
- Upgraded the managed global routing block with native defaults and per-task strict handoff while leaving other plugins untouched.

## 0.3.0 - 2026-07-11

- Added an optional CodexBar 0.41.0-or-later adapter for local token totals, model breakdowns, project filtering, calendar windows, and estimated cost.
- Added bounded JSON and subprocess handling without reading Codex or CodexBar credentials or session files directly.
- Made standard-task explorer and reviewer roles conditional, added a three-start task budget, and encoded primary-executor exclusivity.
- Clarified single-orchestration precedence between Model Economy and Superpowers, distinct review evidence layers, and minimal delegation context.
- Made `verify` reject installed role templates from an older plugin version until they are upgraded.

## 0.2.0 - 2026-07-11

- Added `enable-global-routing` and `disable-global-routing` to manage a global `AGENTS.md` development-routing block safely and idempotently.
- Extended `cost-aware-development` discovery so general software-development tasks can trigger capability-aware routing.
- Kept the global rule cross-project and free of business context; a project's own `AGENTS.md` can override it.

## 0.1.0 - 2026-07-11

- First public release with capability-aware role routing, replaceable model profiles, and a local lifecycle CLI.
- Added cross-platform CI, sensitive-content checks, and a public security-reporting path.
- Added local 0.1.0 preview evaluation covering temporary-home lifecycle tests, static installation review, cross-project discovery, and public-report boundaries.
- Exposed `upgrade --dry-run` for lifecycle integration verification.
- Expanded sensitive-content scanning and fail-closed Git reading, including annotated tags.
- Restored original POSIX file permissions during transactional rollback and documented forced-uninstall ownership behavior.
- Fixed UTF-8 handling on Windows default code pages.
