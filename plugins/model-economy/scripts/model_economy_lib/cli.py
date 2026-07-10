"""Command-line orchestration for Model Economy's local lifecycle."""

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

from .config import ConfigError, export_profile, import_profile, load_config
from .doctor import SmokeReport, run_doctor, run_smoke, verify_installation
from .filesystem import resolve_codex_home
from .lifecycle import ChangeSet, ConflictError, Context, install, plan_upgrade, uninstall, upgrade
from .models import Profile
from .profiles import load_profile


SUCCESS = 0
ENVIRONMENT_FAILURE = 1
CONFLICT = 2
PARAMETER_ERROR = 64

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIRECTORY = PLUGIN_ROOT / "assets" / "profiles"
PROFILE_NAMES = tuple(path.stem for path in sorted(PROFILE_DIRECTORY.glob("*.toml")))


class UsageError(ValueError):
    """Raised for invalid command-line usage without terminating the caller."""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def _add_location_options(parser: argparse.ArgumentParser, *, suppressed: bool = False) -> None:
    default = argparse.SUPPRESS if suppressed else None
    parser.add_argument("--codex-home", type=Path, default=default)
    parser.add_argument("--codex-bin", default=default)


def _build_parser() -> Parser:
    parser = Parser(prog="model_economy", description="管理 Model Economy 角色配置")
    _add_location_options(parser)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, **kwargs: object) -> argparse.ArgumentParser:
        child = commands.add_parser(name, **kwargs)
        _add_location_options(child, suppressed=True)
        return child

    install_parser = command("install")
    install_parser.add_argument("--profile", choices=PROFILE_NAMES, required=True)
    install_parser.add_argument("--force", action="store_true")

    configure_parser = command("configure")
    configure_parser.add_argument("--profile", choices=PROFILE_NAMES)
    configure_parser.add_argument("--strong")
    configure_parser.add_argument("--balanced")
    configure_parser.add_argument("--economy")
    configure_parser.add_argument("--force", action="store_true")

    verify_parser = command("verify")
    verify_parser.add_argument("--quiet", action="store_true")

    doctor_parser = command("doctor")
    doctor_parser.add_argument("--smoke", action="store_true")

    upgrade_parser = command("upgrade")
    upgrade_parser.add_argument("--dry-run", action="store_true")
    upgrade_parser.add_argument("--force", action="store_true")

    export_parser = command("export-profile")
    export_parser.add_argument("path", type=Path)

    import_parser = command("import-profile")
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument("--force", action="store_true")

    uninstall_parser = command("uninstall")
    uninstall_parser.add_argument("--purge", action="store_true")
    uninstall_parser.add_argument("--force", action="store_true")
    return parser


def _context(codex_home: Path | None) -> Context:
    home = (
        codex_home.expanduser().resolve()
        if codex_home is not None
        else resolve_codex_home(os.environ)
    )
    return Context(home, PLUGIN_ROOT, "0.1.0")


def _load_bundled_profile(name: str) -> Profile:
    return load_profile(PROFILE_DIRECTORY / f"{name}.toml")


def _custom_profile(args: argparse.Namespace) -> Profile:
    supplied = {name: getattr(args, name) for name in ("strong", "balanced", "economy")}
    if args.profile is not None:
        if any(value is not None for value in supplied.values()):
            raise UsageError("--profile 不能与单独模型参数同时使用")
        return _load_bundled_profile(args.profile)
    if any(value is None for value in supplied.values()):
        raise UsageError("configure 需要 --profile 或完整的 --strong/--balanced/--economy")
    return Profile("custom", False, supplied)


def _imported_profile(path: Path) -> Profile:
    name, models = import_profile(path)
    if models and set(models) != {"strong", "balanced", "economy"}:
        raise ConfigError("导入档案的模型映射必须完整")
    return Profile(name, not models, models)


def _print_changes(changes: ChangeSet) -> None:
    print(
        "完成："
        f"新增 {len(changes.created)}，更新 {len(changes.updated)}，"
        f"移除 {len(changes.removed)}，未变更 {len(changes.unchanged)}。"
    )


def _print_verification(checks: dict[str, bool]) -> None:
    label = "通过" if all(checks.values()) else "失败"
    print(f"本地验证：{label}")


def _print_doctor(checks: dict[str, bool], codex_available: bool) -> None:
    print(f"诊断：{'通过' if all(checks.values()) else '失败'}")
    if not codex_available:
        print("Codex：未找到")


def _print_smoke(smoke: SmokeReport) -> None:
    print(f"Subagent 启动：{'通过' if smoke.subagent_started else '失败'}")
    print("角色身份：未验证（当前 Codex JSONL 不含 agent_type）")
    print("模型身份：未验证")


def _run(args: argparse.Namespace) -> int:
    context = _context(args.codex_home)
    if args.command == "install":
        _print_changes(install(context, _load_bundled_profile(args.profile), args.force))
        return SUCCESS
    if args.command == "configure":
        _print_changes(install(context, _custom_profile(args), args.force))
        return SUCCESS
    if args.command == "verify":
        report = verify_installation(context)
        if not args.quiet:
            _print_verification(report.checks)
        return SUCCESS if report.ok else ENVIRONMENT_FAILURE
    if args.command == "doctor":
        report = run_doctor(context, args.codex_bin)
        _print_doctor(report.checks, report.codex_available)
        if args.smoke:
            smoke = run_smoke(context, args.codex_bin)
            _print_smoke(smoke)
            return SUCCESS if report.ok and smoke.subagent_started else ENVIRONMENT_FAILURE
        return SUCCESS if report.ok else ENVIRONMENT_FAILURE
    if args.command == "upgrade":
        changes = plan_upgrade(context) if args.dry_run else upgrade(context, args.force)
        if changes.conflicts:
            paths = ", ".join(str(path) for path in changes.conflicts)
            raise ConflictError(f"unmanaged paths: {paths}")
        _print_changes(changes)
        return SUCCESS
    if args.command == "export-profile":
        export_profile(load_config(context.config_path), args.path)
        print("档案已导出。")
        return SUCCESS
    if args.command == "import-profile":
        _print_changes(install(context, _imported_profile(args.path), args.force))
        return SUCCESS
    if args.command == "uninstall":
        changes = uninstall(context, args.purge, args.force)
        if changes.conflicts:
            return CONFLICT
        _print_changes(changes)
        return SUCCESS
    raise UsageError("未知命令")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return a stable process exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        return _run(args)
    except UsageError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return PARAMETER_ERROR
    except ConflictError as exc:
        print(f"冲突：{exc}", file=sys.stderr)
        return CONFLICT
    except (ConfigError, OSError, ValueError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return ENVIRONMENT_FAILURE
