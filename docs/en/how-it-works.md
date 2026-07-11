[简体中文](../zh-CN/how-it-works.md)

# How it works

Model Economy is a workflow policy, not an automated claim about model quality or spend. The policy classifies work first, then limits which roles can participate.

## Classification order

Classification is `first_match` in this order:

1. **Large or high-risk** when any high-risk boundary, new architecture, or wide blast radius is present.
2. **Mechanical** only when all five economy conditions are true: deterministic inputs and rules, independent retryable operations, no sensitive or high-risk boundary, automated per-result checks, and bounded explicit failure.
3. **Simple** only when files are known, no open judgment remains, verification is direct, and there is no creative or behavioral change.
4. **Standard** is the fallback.

## Capability gates

| Class | Role and capability rules | `strong` maximum |
| --- | --- | --- |
| Large or high-risk | `architect` completes a read-only decision before design approval; `explorer` provides read-only fact collection; `implementer` works after approval; `final-reviewer` completes review after verification | 2 |
| Mechanical | Only `batch-worker` may perform the fixed-rule work | 0 |
| Simple | The main agent handles it directly | 0 |
| Standard | `implementer`, `reviewer`, and `explorer` are available; after two substantive failures, one diagnostic `architect` call is allowed | 1 |

The counts are policy caps, not a promise that calls are available or that their identities can be independently verified.

## Role boundaries

- `architect` and `final-reviewer` are `strong` and read-only. They do not write plans, patches, or code.
- `implementer` is `balanced` and may write only approved-scope implementation, tests, and verification.
- `reviewer` is `balanced` and read-only.
- `explorer` is `economy` and read-only; it collects minimal facts rather than producing designs or edits.
- `batch-worker` is `economy` and writable only for qualified fixed-rule work with per-item checks.

The main agent retains classification, approval checks, write coordination, risk decisions, and final verification responsibility.

## Approval and verification

Creative or behavioral changes require an approved design or traceable approval evidence before planning or implementation. Literal text-only edits and deterministic work fully contained in an approved specification are the exceptions.

Approved implementation follows test-driven development. Before a completion claim, run the relevant fresh verification and inspect the result. Cost optimization never bypasses approval, testing, verification, or safety checks.

## Delegation hygiene

Before delegating, remove secrets, tokens, personal data, production data, internal URLs, and irrelevant paths. Declare each agent's file set before it writes. Write sets must not overlap; the main agent serializes overlapping work. At most three subagents may run concurrently, and recursive delegation is forbidden.

## Limits

- The policy does not measure token use or establish a savings baseline.
- Current smoke output can observe subagent startup only; role and model identity are unverified.
- Project instructions can supersede global routing where applicable.

See [Installation](installation.md) for setup and [CLI reference](cli-reference.md) for local commands.
