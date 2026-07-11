[简体中文](SECURITY.zh-CN.md)

# Security Policy

## Supported versions

Only the latest released version is supported. Upgrade before reporting an issue when possible.

## Private reporting

Do not disclose vulnerabilities, credentials, private paths, or exploit details in public issues, discussions, or commits. Use GitHub Security Advisories and select **Report a vulnerability** for a private report.

Include the affected version, reproduction steps, impact, and an optional remediation proposal. Use the smallest useful example and remove sensitive material. Maintainers will acknowledge the report in the advisory, assess impact, and coordinate a fix and disclosure when appropriate.

## Trust boundaries

The CLI manages Model Economy configuration, declared agent files under `CODEX_HOME`, and the marked, managed Model Economy block in `$CODEX_HOME/AGENTS.md`; it does not manage credentials or validate model and role identity. Configuration corruption or ownership conflicts fail closed. Only an explicit user-authorized `--force` operation overrides the relevant ownership or conflict guard. Details are in the [README](README.md).

## Release checks

Maintainers run:

```sh
python3 scripts/check_sensitive_content.py .
python3 -m unittest discover -s tests -v
```

The sensitive-content check covers the worktree and every reachable Git commit's author and committer emails, messages, paths, and text blobs. It reports relative paths, line numbers, and rule names without printing matched content.
