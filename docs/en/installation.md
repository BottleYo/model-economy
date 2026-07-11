[简体中文](../zh-CN/installation.md)

# Installation

## Prerequisites

- Python 3.11 or later. The runtime uses only the standard library.
- Codex CLI with `plugin marketplace add` and `plugin add`. Check with `codex plugin --help`.
- Git when you want sensitive-content checks to inspect reachable history. Without Git history, the scan checks the worktree only.

Linux, macOS, and Windows are supported. On Windows, use `py -3.11` where this guide uses `python3`.

## Install the plugin

Clone the public repository, add its marketplace, then add the plugin:

```sh
git clone https://github.com/BottleYo/model-economy.git
cd model-economy
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
```

Install one bundled profile:

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile inherited
python3 plugins/model-economy/scripts/model_economy.py install --profile openai-56
```

`inherited` leaves agent model selection to the current Codex configuration. `openai-56` writes the bundled three-tier mapping. Run only one command for an initial setup.

## Configure a custom profile

Supply all three tiers together:

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>
```

You may also select a bundled profile through `configure --profile inherited` or `configure --profile openai-56`. Use `--force` only after reviewing a managed-file conflict.

## Verify and diagnose

```sh
python3 plugins/model-economy/scripts/model_economy.py verify
python3 plugins/model-economy/scripts/model_economy.py doctor
python3 plugins/model-economy/scripts/model_economy.py doctor --smoke
```

`doctor --smoke` checks whether a subagent starts. It does not verify role or model identity.

## Enable global routing

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

These commands manage only the Model Economy block in `$CODEX_HOME/AGENTS.md`. Enabling is idempotent; disabling restores the previous text outside the managed block. A project-level `AGENTS.md` can override the global instructions.

## Upgrade

`codex plugin marketplace upgrade` refreshes Git marketplace snapshots only; it does not refresh a marketplace added from a local path. Update the checkout, re-register the local marketplace, reinstall the plugin snapshot, then inspect and apply the managed-file upgrade:

```sh
git pull --ff-only
codex plugin remove model-economy@model-economy-public
codex plugin marketplace remove model-economy-public
codex plugin marketplace add .
codex plugin add model-economy@model-economy-public
python3 plugins/model-economy/scripts/model_economy.py upgrade --dry-run
python3 plugins/model-economy/scripts/model_economy.py upgrade
```

`--force` overwrites a conflicting managed file. Resolve the diff first whenever possible.

## Export and import a profile

```sh
python3 plugins/model-economy/scripts/model_economy.py export-profile <path>
python3 plugins/model-economy/scripts/model_economy.py import-profile <path>
```

An imported profile with an explicit model mapping must include `strong`, `balanced`, and `economy`.

## Uninstall

```sh
python3 plugins/model-economy/scripts/model_economy.py uninstall
python3 plugins/model-economy/scripts/model_economy.py uninstall --purge
codex plugin remove model-economy@model-economy-public
```

Plain uninstall keeps local plugin configuration. `--purge` also removes managed configuration. Plugin removal does not remove global routing automatically; run `disable-global-routing` first if that is intended.

## Alternate Codex location

Every local command accepts `--codex-home <directory>`. `doctor` additionally accepts `--codex-bin <command>` to choose the Codex executable it diagnoses.

Continue with [How it works](how-it-works.md) or the [CLI reference](cli-reference.md).
