[简体中文](../zh-CN/cli-reference.md)

# CLI reference

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

## `configure`

```sh
python3 plugins/model-economy/scripts/model_economy.py configure --profile {inherited,openai-56} [--force]
python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model> [--force]
```

Use either `--profile` or all three explicit model arguments, never both.

## `verify`

```sh
python3 plugins/model-economy/scripts/model_economy.py verify [--quiet]
```

Checks the local installation. `--quiet` suppresses the human-readable report.

## `doctor`

```sh
python3 plugins/model-economy/scripts/model_economy.py doctor [--smoke]
```

Diagnoses local prerequisites and installation state. `--smoke` attempts a subagent launch. It does not verify role or model identity.

## `upgrade`

```sh
python3 plugins/model-economy/scripts/model_economy.py upgrade [--dry-run] [--force]
```

`--dry-run` reports the managed changes without writing them. `--force` overwrites conflicting managed files.

## `export-profile` and `import-profile`

```sh
python3 plugins/model-economy/scripts/model_economy.py export-profile <path>
python3 plugins/model-economy/scripts/model_economy.py import-profile <path> [--force]
```

Export writes the current profile. Import installs a profile from a file; explicit mappings must provide all three tiers.

## `uninstall`

```sh
python3 plugins/model-economy/scripts/model_economy.py uninstall [--purge] [--force]
```

Without `--purge`, local plugin configuration is retained. `--force` bypasses state ownership proof for the fixed Model Economy agent-file names; use it only when those files should be removed.

## `enable-global-routing` and `disable-global-routing`

```sh
python3 plugins/model-economy/scripts/model_economy.py enable-global-routing
python3 plugins/model-economy/scripts/model_economy.py disable-global-routing
```

These commands add or remove only the managed Model Economy block in `$CODEX_HOME/AGENTS.md`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Command succeeded. |
| `1` | Environment, configuration, validation, or I/O failure. |
| `2` | Managed-file conflict. |
| `64` | Invalid CLI usage or parameters. |

For setup guidance, see [Installation](installation.md). For routing behavior, see [How it works](how-it-works.md).
