[简体中文](CHANGELOG.zh-CN.md)

# Changelog

This project follows Semantic Versioning. Notable changes are recorded here.

## 0.5.0 - 2026-07-13

- Added three on-demand lightweight leaf skills: `domain-context`, `module-design`, and `disposable-prototype`.
- Kept leaf skills at zero subagent starts with no task-classification, model-routing, or commit authority; production implementation remains under Model Economy's single orchestration authority.
- Added isolation and explicit bans on real accounts, external writes, destructive side effects, and all credential sources for disposable prototypes.
- Encoded lightweight triggers and outputs in the machine routing policy while keeping the six roles and `strong` limits unchanged.

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
