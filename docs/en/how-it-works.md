[简体中文](../zh-CN/how-it-works.md)

# How it works

> This describes the v0.7.0 routing contract. Live visible-task trials were waived for release and remain unverified. These rules are not a platform-enforced scheduler. For previous behavior, use the v0.6.1 tag.

Model Economy is a workflow policy, not an automated claim about model quality or spend. The policy classifies work first, then limits which roles can participate.

## Installation modes

- **Core:** all skills run without local six-role configuration. Simple work stays with the main agent. Mechanical and standard work also defaults to the main agent, with visible implementation available only when explicitly authorized and supported by the host. Native quality gates remain; no custom role or independent model identity is claimed.
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

| Class | Role and capability rules | Strong role slots | Strong execution requests |
| --- | --- | --- | --- |
| Large or high-risk | Read-only `architect` decision before approval; choose the main agent, `implementer`, or an authorized visible implementer; independent `final-reviewer` after verification | 2 | At most 4 |
| Mechanical | All five conditions must hold; choose `batch-worker` or an authorized visible task with economy duties and per-item checks | 0 | 0 |
| Simple | Main agent, no delegation | 0 | 0 |
| Standard | Choose the main agent, `implementer`, or an authorized visible task; other roles remain conditional | 1 | At most 2 |

Slots count distinct strong duties, not calls. Each allowed strong role can execute at most twice: an initial judgment plus a justified clarification, or final review plus a post-fix review. Spare requests require concrete evidence and cannot move between roles. All count toward the total execution budget below. These are policy-level caps, not proof of availability or identity.

## Role boundaries

- `architect` and `final-reviewer` are `strong` and read-only. They do not write plans, patches, or code.
- `implementer` is `balanced` and may write only approved-scope implementation, tests, and verification.
- `reviewer` is `balanced` and read-only.
- `explorer` is `economy` and read-only; it collects minimal facts rather than producing designs or edits.
- `batch-worker` is `economy` and writable only for qualified fixed-rule work with per-item checks.

The main agent retains classification, approval checks, write coordination, risk decisions, and final verification responsibility.

When large/high-risk work needs additional facts, `explorer` provides read-only fact collection. It still consumes the root budget and is not an automatic extra stage.

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

For standard work, `explorer` is allowed only when file locations, dependencies, or existing facts are uncertain. `reviewer` is allowed only for cross-module or critical logic changes, non-obvious regression risk, or material test-coverage doubt. Two substantive failures or concrete capability-mismatch evidence can justify a read-only architect diagnosis. Record the evidence and narrow the question first, rather than retrying blindly. Reclassify when high risk is discovered without resetting past budget use.

## Visible-task channel

Installation mode and execution channel are independent. Desktop tools do not prove enhancement health. `visible_task` is a generic execution target, not a seventh role or a claim to custom role identity.

- `auto` delegates only when useful; `visible-first` prefers visible tasks; `current-only` does not initiate delegation. Preferences do not grant creation authority.
- Creation requires an explicit user request or standing work-package creation authorization in user-confirmed, trusted project rules. Stricter current host-tool requirements still take precedence and cannot be bypassed by project rules. Check the actual project, starting state, file ownership, model, and reasoning request first. Git defaults to worktrees unless the user explicitly chooses the shared checkout; non-Git uses the actual shared directory.
- Requiring all delegated work to be visible means `all_delegated` by default. Use `implementation` only when the user explicitly limits the scope. Do not silently replace in-scope visible tasks with internal agents.
- A read-only prompt is not a read-only sandbox. Stop and report missing mandatory role permissions. Strict all-visible high-risk work cannot silently switch to internal review or reduced assurance.
- Choose exactly one primary executor per implementation unit. Reuse the original task for direct fixes; changing models does not require changing tasks. Never silently substitute a rejected model/effort pair. Omitted fields use host defaults on creation and retain settings on continuation; neither proves a downgrade.
- A pending creation ID is not a ready task ID. Reconcile uncertain responses before another creation request. Without a model echo, record only that the request was submitted and the runtime configuration is unconfirmed; identity stays unverified.
- Delivery enters awaiting-integration status. Complete only after checking the integrated tree and evidence. Ownership is not a hard lock, and two independently passing worktrees do not prove integration.

Load the [visible-task contract](../../plugins/model-economy/skills/cost-aware-development/references/visible-tasks.md) only when relevant. The official [worktree documentation](https://learn.chatgpt.com/docs/environments/git-worktrees) explains isolation and starting state; current tool definitions govern exact parameters. Under full Superpowers, Model Economy does not dispatch visible tasks or orchestrate work packages.

## Root work-package budget

For one acceptance goal, internal agents and visible tasks share at most 3 new execution contexts and 6 delegated execution requests. Default concurrency is at most 2, with at most 3 for independent responsibilities; filling the slots is never required. Continuations, retries, and reruns after model changes count. Status reads and clarification messages that do not trigger execution do not count.

Reserve before calling. Release a reservation only for a confirmed non-start. Pending creation, uncertain responses, and failures after startup retain their reservations until reconciled. Child packages, coordinator changes, and reclassification do not reset use. Include observed user continuations in the sidebar; incomplete history blocks further dispatch until reconciled. Going beyond a cap needs explicit user expansion, not a generic “continue.”

This is an orchestration budget, not a total token cap; the main coordinator also consumes usage. Reuse an existing task table, and create a record at an agreed location only for actual delegation or cross-task continuity. Do not copy full chats or credentials.

## Approval and verification

Traceable approval is required before implementation when goals are materially ambiguous, approaches produce materially different outcomes, a high-risk decision is involved, or an architecture boundary is unapproved. Clear acceptance criteria, reproducible bug fixes, approved-scope implementation, and deterministic work do not repeat approval.

Before a completion claim, run the relevant fresh verification and inspect the result. Cost optimization never bypasses necessary approval, risk-appropriate testing, verification, or safety checks.

Review evaluates the change, final review evaluates residual delivery risk for large or high-risk work, and completion verification validates fresh evidence. These are distinct evidence layers rather than repeated full reviews.

## Delegation hygiene

Before delegating, remove secrets, tokens, personal data, production data, internal URLs, and irrelevant paths. Include explicit non-goals and verification commands. Declare file ownership, including test/build outputs. Parallel write sets must not overlap; the main agent serializes overlap. Child tasks cannot delegate recursively. One coordinator owns records, budgets, and integration; archiving or closing a record does not release ownership while work is still running.

## Limits

- Optional CodexBar summaries show local usage and estimated cost, but do not establish a savings baseline or role attribution.
- Current smoke output can observe subagent startup only; role and model identity are unverified.
- Project instructions can supersede global routing where applicable.

See [Installation](installation.md) for setup and [CLI reference](cli-reference.md) for local commands.
