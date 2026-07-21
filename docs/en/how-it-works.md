[简体中文](../zh-CN/how-it-works.md)

# How it works

Model Economy is a workflow policy, not an automated claim about model quality or spend. The policy classifies work first, then limits which roles can participate.

## Installation modes

- **Core:** all skills run without local six-role configuration. Simple, mechanical, and standard tasks use the main agent with native quality gates. No custom role or independent model identity is claimed.
- **Enhanced:** all six managed role files, hashes, mapping, and template version must be healthy before six-role routing is allowed.
- **Degraded:** partial, conflicting, or outdated enhancement artifacts fail closed and are never silently treated as core.

Core mode cannot satisfy isolated architect and final-reviewer gates for large/high-risk work. It reports that limitation and asks the user to install enhanced mode or explicitly approve a reduced-assurance single-agent path. The latter is never reported as the complete Model Economy high-risk workflow.

## Classification order

Classification is `first_match` in this order:

1. **Large or high-risk** when any high-risk boundary, new architecture, or wide blast radius is present.
2. **Mechanical** only when all five economy conditions are true: deterministic inputs and rules, independent retryable operations, no sensitive or high-risk boundary, automated per-result checks, and bounded explicit failure.
3. **Simple** only when files are known, no open judgment remains, verification is direct, and there is no creative or behavioral change.
4. **Standard** is the fallback.

## Enhanced-mode capability gates

| Class | Role and capability rules | `strong` maximum |
| --- | --- | --- |
| Large or high-risk | `architect` completes a read-only decision before design approval; `explorer` provides read-only fact collection; `implementer` works after approval; `final-reviewer` completes review after verification | 2 |
| Mechanical | Only `batch-worker` may perform the fixed-rule work | 0 |
| Simple | The main agent handles it directly | 0 |
| Standard | The main agent or one `implementer` performs the primary implementation; `explorer` and `reviewer` are conditional; after two substantive failures, one diagnostic `architect` call is allowed | 1 |

The counts are policy caps, not a promise that calls are available or that their identities can be independently verified.

## Role boundaries

- `architect` and `final-reviewer` are `strong` and read-only. They do not write plans, patches, or code.
- `implementer` is `balanced` and may write only approved-scope implementation, tests, and verification.
- `reviewer` is `balanced` and read-only.
- `explorer` is `economy` and read-only; it collects minimal facts rather than producing designs or edits.
- `batch-worker` is `economy` and writable only for qualified fixed-rule work with per-item checks.

The main agent retains classification, approval checks, write coordination, risk decisions, and final verification responsibility.

## Native quality kernel

Model Economy includes four conditional quality gates. The intent gate blocks implementation only for material ambiguity, high-risk decisions, or unapproved architecture boundaries. The planning gate lets simple work proceed directly, uses short plans for standard work, and reserves durable plans for large work. The testing gate scales test-first discipline or alternative checks to behavioral risk. The evidence gate requires fresh verification before completion.

These gates are not a fixed pipeline. Clear goals and acceptance criteria do not require repeat design approval. Documentation, formatting, and deterministic configuration do not require formal TDD. Failed or unavailable verification must be disclosed.

## Lightweight engineering skills

Model Economy can load three focused leaf skills without changing routing:

| Skill | Trigger | Output |
| --- | --- | --- |
| `domain-context` | Domain vocabulary, invariants, or ADRs directly affect the task | Minimal vocabulary, constraints, and documented conflicts |
| `module-design` | Module boundaries, coupling, or change surface need evaluation | Boundary findings, interface tradeoffs, and the smallest improvement |
| `disposable-prototype` | A small experiment is cheaper than more discussion about one concrete unknown | Isolated experiment, observed result, and production decision input |

Leaf skills have `classification_effect: none` and `subagent_starts: 0`. They do not own orchestration, add plans or reviews, or commit on their own. Prototypes must not use any real account, cause any external write or destructive side effect, or obtain credentials from files, environment variables, keychains, token caches, or raw session databases. Production code still passes through the approval, testing, and verification required by its task class.

## One orchestration authority and Superpowers

Instruction priority selects one orchestration workflow. Model Economy is the default source for role topology, capability tiers, subagent budgets, and completion gates. Installing, enabling, or discovering Superpowers does not authorize its full workflow.

Model Economy hands off the current task only when the user explicitly requests “full Superpowers” or “Superpowers strict mode.” After handoff, Model Economy provides model and cost advice only. A request for one method such as test-first development, systematic debugging, or completion verification is not strict authorization, and handoff state never persists across tasks.

For standard work, `explorer` is allowed only when file locations, dependencies, or existing facts are uncertain. `reviewer` is allowed only for cross-module or critical logic changes, non-obvious regression risk, or material test-coverage doubt. A task may start at most three subagents in total; reclassification does not reset that budget.

## Approval and verification

Traceable approval is required before implementation when goals are materially ambiguous, approaches produce materially different outcomes, a high-risk decision is involved, or an architecture boundary is unapproved. Clear acceptance criteria, reproducible bug fixes, approved-scope implementation, and deterministic work do not repeat approval.

Before a completion claim, run the relevant fresh verification and inspect the result. Cost optimization never bypasses necessary approval, risk-appropriate testing, verification, or safety checks.

Review evaluates the change, final review evaluates residual delivery risk for large or high-risk work, and completion verification validates fresh evidence. These are distinct evidence layers rather than repeated full reviews.

## Delegation hygiene

Before delegating, remove secrets, tokens, personal data, production data, internal URLs, and irrelevant paths. Include explicit non-goals and verification commands. Declare each agent's file set before it writes. Write sets must not overlap; the main agent serializes overlapping work. At most three subagents may start during the task, no more than three may run concurrently, and recursive delegation is forbidden.

## Limits

- Optional CodexBar summaries show local usage and estimated cost, but do not establish a savings baseline or role attribution.
- Current smoke output can observe subagent startup only; role and model identity are unverified.
- Project instructions can supersede global routing where applicable.

See [Installation](installation.md) for setup and [CLI reference](cli-reference.md) for local commands.
