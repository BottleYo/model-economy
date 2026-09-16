[简体中文](../zh-CN/cli-reference.md)

# CLI reference

> v0.7.0 includes role overrides, config schema 2, and migration backups. Older tags do not provide these new options. State and status JSON remain schema 1.

Run the local CLI from the repository root:

```sh
python3 plugins/model-economy/scripts/model_economy.py <command>
```

On Windows, replace `python3` with `py -3.11`. Every command accepts `--codex-home <directory>`; `doctor` also accepts `--codex-bin <command>`.

## `install`

```sh
python3 plugins/model-economy/scripts/model_economy.py install --profile {inherited,openai-56} [--force]
```

Installs one bundled profile. `--force` overwrites conflicting managed files.

In v0.7.0, `install` also accepts the `--role-model` and `--reasoning` overrides described below. `--profile` remains required.

For an existing managed schema 1 installation, `install` refuses the operation and asks you to run `upgrade` first, even with `--force`. Reinstallation cannot skip migration backups or silently change legacy reasoning. Use `configure` when you intentionally want to reset the profile.

## `configure`

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --profile {inherited,openai-56} [--force]
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model> [--force]
```

Use either `--profile` or all three explicit model arguments, never both.

In v0.7.0, `configure` can override role models and reasoning independently on top of the selected base profile:

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --profile inherited --reasoning model-economy-implementer=medium --reasoning model-economy-explorer=low
python3 plugins/model-economy/scripts/model_economy.py configure --profile openai-56 --role-model model-economy-implementer=MODEL_IMPLEMENTATION --reasoning model-economy-implementer=medium
```

Replace `MODEL_IMPLEMENTATION` with a model identifier. It is a placeholder, not a verified available model.

- Repeat `--reasoning ROLE=LEVEL` and `--role-model ROLE=MODEL` for different roles; duplicate roles within either option are rejected.
- Use the full name of one of the six roles. `LEVEL` accepts only `low`, `medium`, or `high`.
- Role model overrides take precedence over capability mappings. Reasoning is configured separately. Inherited profiles reject partial model overrides; explicit profiles require all three capability mappings.
- `configure` rebuilds configuration from the selected base profile; it is not a one-field edit of the existing installation. Supply every override you want to retain.
- Fresh installations and explicit configuration use lean defaults: high for architect/final-reviewer, medium for implementer/reviewer, and low for explorer/batch-worker. Normal upgrades preserve existing effective values.
- These settings describe role requests. They do not switch the current main conversation's model, query account model catalogs, or verify model identity.

## `verify`

```sh
python3 plugins/model-economy/scripts/model_economy.py verify [--quiet]
```

Checks the local installation, including whether managed role models and reasoning match the configuration. `--quiet` suppresses the human-readable report.

## `doctor`

```sh
python3 plugins/model-economy/scripts/model_economy.py doctor [--smoke]
```

Checks local prerequisites, managed installation state, and whether `codex --version` responds. Plain `doctor` does not invoke the broader `codex doctor`, inspect authentication, or scan session and database artifacts. `--smoke` explicitly opts into an ephemeral authenticated Codex run that attempts a subagent launch and may consume usage. Neither mode verifies role or model identity.

## `status`

```sh
python3 plugins/model-economy/scripts/model_economy.py status [--format text|json]
```

Reports the plugin version and inferred `core`, `enhanced`, or `degraded` mode. It reads only Model Economy's own config, state, and six declared role paths; it performs no network or subprocess call. JSON uses stable `status_schema_version: 1`. Core and healthy enhanced modes return `0`; degraded state returns `1`, or `2` for an ownership/hash conflict. Identity fields are always `false`. `core` means only that the local six-role enhancement is absent; it does not prove that the plugin is installed or enabled in Codex.

## `upgrade`

```sh
python3 plugins/model-economy/scripts/model_economy.py upgrade [--dry-run] [--force]
```

`--dry-run` reports the managed changes without writing them. `--force` overwrites conflicting managed files.

v0.7.0 reads config schema 1/2 and writes schema 2; state and status JSON remain at schema 1. Migration validates the original config and role hashes before preserving effective valid reasoning values. It does not silently apply fresh-install defaults. The preview shows schema, model, and reasoning changes without creating a backup.

Before migration, a unique directory under `$CODEX_HOME/model-economy/backups/` stores the original managed artifacts and permission information needed for recovery. Backup failure leaves the installation unchanged; transaction failure restores its previous artifacts. Repeated upgrades should perform zero writes. `--force` does not make symlinks, hard links, or invalid configuration safe. See the [installation guide](installation.md) for recovery.

A v1-to-v2 migration requires matching ownership hashes for the old config and roles even with `--force`; resolve conflicts first. Existing v2 installations can still use `--force` for ordinary content ownership conflicts, while filesystem safety checks remain in place.

## `export-profile` and `import-profile`

```sh
python3 plugins/model-economy/scripts/model_economy.py export-profile <path>
python3 plugins/model-economy/scripts/model_economy.py import-profile <path> [--force]
```

Export writes the current profile. Import installs a profile from a file; explicit mappings must provide all three tiers.

v0.7.0 exports schema 2 with role model overrides and complete six-role reasoning; imports accept schema 1/2. Old profiles retain legacy reasoning defaults. Export does not migrate the installation and excludes installation hashes, project paths, task identifiers, and account data. Schema 2 profiles require v0.7.0+ tools.

## `uninstall`

```sh
python3 plugins/model-economy/scripts/model_economy.py uninstall [--purge] [--force]
```

Without `--purge`, local plugin configuration is retained. `--force` bypasses state ownership proof for the fixed Model Economy agent-file names; use it only when those files should be removed.

`uninstall --purge` does not automatically delete migration backups.

## `enable-global-routing` and `disable-global-routing`

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

These commands add or remove only the managed Model Economy block in `$CODEX_HOME/AGENTS.md`.

## `usage`

```sh
python3 plugins/model-economy/scripts/model_economy.py usage [--days 1..365] [--project <path>] [--format text|json] [--codexbar-bin <path>]
```

Reads local CodexBar 0.41.0-or-later cost JSON. The default is the last 30 calendar days. `--project` selects an exact project path but public output contains only its directory name. `--format json` emits Model Economy's stable `usage_schema_version: 1` envelope.

CodexBar is an optional third-party local program. Model Economy does not read its credentials or session files, but it cannot guarantee CodexBar's internal behavior. Costs are CodexBar estimates; role attribution and model identity remain unverified. macOS and Linux support normal CLI discovery. On Windows, provide a compatible executable explicitly with `--codexbar-bin` or `CODEXBAR_BIN`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Command succeeded. |
| `1` | Environment, configuration, validation, or I/O failure. |
| `2` | Managed-file conflict. |
| `64` | Invalid CLI usage or parameters. |

For setup guidance, see [Installation](installation.md). For routing behavior, see [How it works](how-it-works.md).
