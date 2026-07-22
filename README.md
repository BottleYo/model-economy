[简体中文](README.zh-CN.md)

# Model Economy

> Use strong models for decisions, not routine work.

![Model Economy](assets/social-preview.png)

When one workflow gives a configuration edit, a known bug, and an architecture change the same treatment, every task pays for questions, a specification, a long plan, multiple subagents, and several reviews. That rigor is valuable when the risk justifies it. On routine work, it adds cost and waiting without improving the decision.

Model Economy makes risk classification the first step. The result is not just a model router: it is a bounded development workflow that controls which capability tier may act, what each role may change, when approval is required, and how much orchestration a task can consume.

It can also display local CodexBar token and estimated-cost summaries. It does not scan sessions itself, promise savings, verify model or role identity, or replace engineering judgment.

## Why it exists

- A one-line fix should not automatically become a project ceremony.
- A high-risk design should still receive strong architecture judgment and an independent final review.
- The agent should have policy-level limits, not an open-ended invitation to spawn more agents or escalate models.
- Completion should mean fresh evidence proportionate to the change, not merely a confident status message.

## What makes it different

| Constraint | What it changes in practice |
| --- | --- |
| Risk comes before routing | Every task is classified as simple, standard, mechanical, or large/high-risk before a role or model tier is selected. |
| Strong calls have policy-level caps | The task-class maximum is `0`, `1`, or `2`; these are routing-policy limits, not proof of model identity or platform-enforced quotas. |
| Roles have permissions | The strong architect and final reviewer are read-only. Implementation stays with `balanced`; fixed-rule batch edits may use `economy`. |
| Orchestration is bounded | A task may start at most three subagents, recursive delegation is prohibited, and small work normally starts none. |
| Quality gates scale with risk | Intent, approval, planning, testing, and completion evidence are native gates, but routine work does not inherit a full methodology. |
| One workflow owns the task | Model Economy does not silently stack another orchestrator on top. A full Superpowers handoff requires explicit authorization for the current task. |

Three optional leaf skills keep context work small: `domain-context` extracts only relevant business constraints, `module-design` checks boundaries and change surface, and `disposable-prototype` answers a concrete unknown with throwaway code. None of them starts subagents or takes over orchestration.

## Model Economy vs full Superpowers

[Superpowers](https://github.com/obra/superpowers) describes itself as a **complete software development methodology** with mandatory workflows for brainstorming, design approval, planning, worktrees, test-driven development, task execution, review, and branch completion. That coherent end-to-end process is useful when you want the full discipline on every eligible task. Model Economy targets a different default: apply only the process justified by the task's risk.

| | Model Economy | Full Superpowers workflow |
| --- | --- | --- |
| Primary goal | Control capability, cost exposure, permissions, and evidence by risk | Apply a complete development methodology from intent through branch completion |
| Default entry | Classify the task first; simple work can proceed directly | Begin with brainstorming and design clarification for building tasks |
| Plans and tests | Scale to ambiguity and behavioral risk | Detailed plans and strict RED-GREEN-REFACTOR TDD are core workflow requirements |
| Subagents | Conditional, non-recursive, at most three per task | May assign a fresh subagent to each planned task with two-stage review |
| Strong-model budget | Explicit class cap: `0` / `1` / `2` | No comparable capability-tier call cap is specified in the published workflow |
| Best fit | Daily development where routine speed and high-risk rigor must coexist | Tasks where the user explicitly wants the complete methodology |
| Coexistence | Owns the default route; hands off only on an explicit current-task request | Takes orchestration authority only after that explicit handoff |

This is a workflow choice, not a claim that one tool is universally better. If you want full Superpowers for a task, say “full Superpowers” or “Superpowers strict mode”. Model Economy then supplies only capability and cost advice and does not add a second process.

## How it works

![Model Economy task flow](assets/model-economy-flow-en.svg)

Tasks are classified in a fixed order: large or high-risk, mechanical, simple, then standard. The first matching class decides the permitted roles and the maximum number of `strong` calls. See [how it works](docs/en/how-it-works.md) for the complete policy.

The role names in this table describe a healthy **enhanced mode**. In core mode, simple, mechanical, and standard tasks use the main agent; large/high-risk work stops at the compatibility gate described below.

| Example | Enhanced-mode route |
| --- | --- |
| Known configuration key, known file, direct check | Simple: main agent, no subagent, `strong` maximum `0` |
| Repeated edit with a fixed rule, bounded files, and per-item validation | Mechanical: `economy` batch worker, only when all five mechanical conditions hold |
| Cross-module bug with a known product behavior | Standard: `balanced` implementation; explorer or reviewer only when their evidence is needed |
| Authentication, permissions, new architecture, or wide blast radius | Large/high-risk: read-only strong architect, balanced implementation, read-only strong final reviewer; `strong` maximum `2` |

## Core and enhanced modes

Directory-style installation starts in **core mode**. All four skills work without user-level six-role files: simple, mechanical, and standard work stays with the main agent and still uses the native quality gates. Core mode does not claim custom role isolation or independent model mapping.

The repository CLI can add **enhanced mode**. It installs six local role definitions and an inherited or explicit three-tier model mapping. Only a complete, hash-matching, current enhancement is treated as enabled. Partial, modified, or outdated enhancement artifacts are reported as `degraded` and fail closed.

For large/high-risk work in core mode, Model Economy reports that isolated architecture and final-review roles are unavailable. The user may install enhanced mode or explicitly approve a reduced-assurance single-agent path; that path is never described as the complete Model Economy high-risk workflow. Model and role identity remain unverified in both modes.

## Install

```sh
git clone https://github.com/BottleYo/model-economy.git
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
```

This is the formal repository installation path and provides core mode. Start a new task after installation. To add the optional six-role enhancement, use the default `inherited` profile:

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile inherited
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py status
```

Use `py -3.11` in place of `python3` on Windows. Model profiles, global routing, CodexBar usage, upgrade, transfer, and uninstall are advanced options documented in [Installation](docs/en/installation.md) and the [CLI reference](docs/en/cli-reference.md).

## First experience

Try one prompt from each risk level and compare the route with the expectation:

| Prompt | Expected core-mode route |
| --- | --- |
| “Change the known timeout constant from 20 to 30 and run its direct test.” | Simple: main agent, direct verification, no custom role. |
| “Fix this reproducible bug across the parser and renderer, then run focused and regression tests.” | Standard: main agent, short plan and risk-scaled quality gates. |
| “Redesign authentication and migrate existing permissions.” | Large/high-risk: report missing isolated architect/final reviewer and stop for the user’s choice. |

Check the mode with `model_economy.py status --format text|json`. To stop using the plugin for one task, say `This task must not use Model Economy.` To remove enhanced mode while keeping the plugin, run `uninstall`; use `uninstall --purge` to remove its local config and state as well.

## Use it on your terms

Model Economy is controllable at the task, project, global-routing, and plugin levels.

| Scope | How to control it |
| --- | --- |
| Use for one task | Say: `Use Model Economy for this task.` |
| Skip for one task | Say: `This task must not use Model Economy.` |
| Project policy | Add the desired rule to the project's `AGENTS.md`; project instructions override the global rule. |
| Global default | Use `enable-global-routing` or `disable-global-routing` below. |
| Installed plugin | In Codex Desktop, open **Plugins → Installed → Model Economy** and toggle it. Start a new task after changing the toggle. |

Enable the global default from the repository root:

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
```

Disable it without removing the plugin:

```sh
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

The plugin toggle and the global `$CODEX_HOME/AGENTS.md` routing block are independent. To stop Model Economy completely, disable global routing, turn off the installed plugin, and start a new task. To keep the plugin available but opt out occasionally, the one-task instruction is enough.

### View usage

With CodexBar 0.41.0 or later installed, view local Codex usage without exposing account credentials:

```sh
python3 plugins/model-economy/scripts/model_economy.py usage
python3 plugins/model-economy/scripts/model_economy.py usage --days 7 --project .
python3 plugins/model-economy/scripts/model_economy.py usage --format json
```

The adapter reports CodexBar's local token totals, model breakdowns, and estimated cost. It does not attribute tokens to Model Economy roles.

## Task classification

| Class | Conditions | Enhanced-mode default capability | `strong` policy maximum |
| --- | --- | --- | --- |
| Large or high-risk | Any high-risk boundary, new architecture, or wide blast radius | `strong` gates plus `balanced` implementation | 2 |
| Mechanical | All five fixed-rule conditions hold | `economy` batch work | 0 |
| Simple | Known files, no open judgment, direct verification, and no creative or behavioral change | Main agent | 0 |
| Standard | The fallback class | `balanced` | 1 |

## Enhanced-mode roles

| Role | Capability | Access | Responsibility |
| --- | --- | --- | --- |
| `model-economy-architect` | `strong` | Read only | Architecture boundaries, risks, and decisions before high-risk design approval |
| `model-economy-final-reviewer` | `strong` | Read only | Findings, evidence gaps, and residual risk after high-risk verification |
| `model-economy-implementer` | `balanced` | Workspace write | Approved implementation, tests, and verification |
| `model-economy-reviewer` | `balanced` | Read only | Independent findings and regression risks |
| `model-economy-explorer` | `economy` | Read only | Minimal file inventory and facts |
| `model-economy-batch-worker` | `economy` | Workspace write | Fixed-rule edits with per-item checks |

## Lightweight engineering skills

The plugin includes three independently triggered leaf skills:

- `domain-context` extracts only the domain vocabulary, invariants, and ADR constraints needed by the current task.
- `module-design` checks module boundaries, knowledge leakage, and change surface, then suggests the smallest structural improvement.
- `disposable-prototype` answers a concrete unknown with an isolated throwaway experiment instead of treating exploratory code as production work.

These skills start no subagents, do not change task classification, model mapping, the six-role topology, or quality gates, and never commit on their own. Production implementation returns to `cost-aware-development` routing. They are built into the plugin and add no dependency on an external engineering-method plugin.

## Global routing

`enable-global-routing` adds the generic development-routing policy to `$CODEX_HOME/AGENTS.md`. The command is idempotent and changes only the marked, managed Model Economy block. A project's own `AGENTS.md` can override the global rule. `disable-global-routing` removes only that managed block.

## Security and trust boundaries

The local CLI manages only its configuration, its declared agent files under `CODEX_HOME`, and the marked, managed Model Economy block in `$CODEX_HOME/AGENTS.md`. It fails closed on missing, damaged, or conflicting managed state. Only an explicit user-authorized `--force` operation overrides the relevant ownership or conflict guard. It does not manage credentials, project data, unowned files, other plugins, or access control for `CODEX_HOME`.

Plain `doctor` verifies managed local files and checks `codex --version`; it does not invoke the broader `codex doctor`, inspect authentication, or scan session and database artifacts. `doctor --smoke` is a separate explicit opt-in that starts an ephemeral authenticated Codex run and may consume usage.

`doctor --smoke` can observe whether a subagent starts. Current Codex JSONL does not provide `agent_type`, so role identity and model identity remain unverified. Read [Security](SECURITY.md) before reporting a vulnerability.

## Documentation

- [Installation](docs/en/installation.md): prerequisites, install, upgrade, profile transfer, and uninstall.
- [How it works](docs/en/how-it-works.md): classification, role boundaries, approval gates, and limits.
- [CLI reference](docs/en/cli-reference.md): commands, options, and exit codes.
- [Security policy](SECURITY.md): private vulnerability reporting and release checks.
- [Changelog](CHANGELOG.md): released changes.
- [Project website](https://bottleyo.github.io/model-economy/), [Support](SUPPORT.md), [Contributing](CONTRIBUTING.md), and [Roadmap](ROADMAP.md).

## Current limitations

- Usage summaries come from optional CodexBar local statistics; Model Economy does not scan sessions itself or attribute tokens to roles.
- `doctor --smoke` does not verify role or model identity.
- The plugin does not install, toggle, or modify Superpowers; it hands off orchestration only after explicit strict authorization for the current task.
- Global routing does not include project-specific context and is not removed automatically by plugin uninstall.
- The GitHub Pages site is static and uses no telemetry, cookies, or external fonts; this repository is a community open-source project, not an official OpenAI product.

## Contributing

Run the local checks before opening a change:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_sensitive_content.py .
```

For a custom model mapping, pass all three capability tiers on one line:

```sh
# 3. custom
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
py -3.11 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
```

## License

[MIT](LICENSE)
