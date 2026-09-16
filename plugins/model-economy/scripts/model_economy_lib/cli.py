"""Command-line orchestration for Model Economy's local lifecycle."""

import argparse
import json
import os
from pathlib import Path
import stat
import sys
from typing import Sequence

from .config import ConfigError, default_reasoning, export_profile, import_profile_config, load_config
from .doctor import (
    SmokeReport,
    StatusReport,
    inspect_status,
    run_doctor,
    run_smoke,
    status_to_dict,
    verify_installation,
)
from .filesystem import resolve_codex_home
from .global_routing import disable_global_routing, enable_global_routing
from .lifecycle import ChangeSet, ConflictError, Context, install, plan_upgrade, uninstall, upgrade
from .models import Profile, ROLES
from .profiles import load_profile
from .usage import (
    UsageError as UsageDataError,
    UsageSummary,
    check_codexbar_version,
    discover_codexbar,
    fetch_usage,
    summarize_usage,
    usage_to_dict,
)


SUCCESS = 0
ENVIRONMENT_FAILURE = 1
CONFLICT = 2
PARAMETER_ERROR = 64

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIRECTORY = PLUGIN_ROOT / "assets" / "profiles"
PROFILE_NAMES = tuple(path.stem for path in sorted(PROFILE_DIRECTORY.glob("*.toml")))


class UsageError(ValueError):
    """Raised for invalid command-line usage without terminating the caller."""


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def _add_location_options(parser: argparse.ArgumentParser, *, suppressed: bool = False) -> None:
    default = argparse.SUPPRESS if suppressed else None
    parser.add_argument("--codex-home", type=Path, default=default)
    parser.add_argument("--codex-bin", default=default)


def _days_value(value: str) -> int:
    try:
        days = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("天数必须是整数") from exc
    if not 1 <= days <= 365:
        raise argparse.ArgumentTypeError("天数必须在 1 到 365 之间")
    return days


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
    install_parser.add_argument("--role-model", action="append", default=[], metavar="ROLE=MODEL")
    install_parser.add_argument("--reasoning", action="append", default=[], metavar="ROLE=LEVEL")
    install_parser.add_argument("--force", action="store_true")

    configure_parser = command("configure")
    configure_parser.add_argument("--profile", choices=PROFILE_NAMES)
    configure_parser.add_argument("--strong")
    configure_parser.add_argument("--balanced")
    configure_parser.add_argument("--economy")
    configure_parser.add_argument("--role-model", action="append", default=[], metavar="ROLE=MODEL")
    configure_parser.add_argument("--reasoning", action="append", default=[], metavar="ROLE=LEVEL")
    configure_parser.add_argument("--force", action="store_true")

    verify_parser = command("verify")
    verify_parser.add_argument("--quiet", action="store_true")

    doctor_parser = command("doctor")
    doctor_parser.add_argument("--smoke", action="store_true")

    status_parser = command("status")
    status_parser.add_argument("--format", choices=("text", "json"), default="text")

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
    command("enable-global-routing")
    command("disable-global-routing")
    usage_parser = command("usage")
    usage_parser.add_argument("--project", type=Path)
    usage_parser.add_argument("--days", type=_days_value, default=30)
    usage_parser.add_argument("--format", choices=("text", "json"), default="text")
    usage_parser.add_argument("--codexbar-bin", type=Path)
    return parser


def _context(codex_home: Path | None) -> Context:
    home = (
        codex_home.expanduser().resolve()
        if codex_home is not None
        else resolve_codex_home(os.environ)
    )
    return Context(home, PLUGIN_ROOT, "0.7.0")


def _safe_managed_config(context: Context):
    path = context.config_path
    current = path
    while current != context.codex_home:
        if current.is_symlink():
            raise ConfigError("config artifact is not safe to read")
        current = current.parent
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ConfigError("config artifact is not safe to read") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ConfigError("config artifact is not safe to read")
    return load_config(path)


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
    return Profile("custom", False, supplied, reasoning=default_reasoning())


def _parse_role_assignments(values: list[str], *, option: str, allowed: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        role, separator, value = raw.partition("=")
        if not separator or not role or not value:
            raise UsageError(f"{option} 必须使用 ROLE=VALUE 格式")
        if role not in allowed:
            raise UsageError(f"{option} 包含未知角色：{role}")
        if role in result:
            raise UsageError(f"{option} 不能重复指定角色：{role}")
        result[role] = value
    return result


def _with_overrides(profile: Profile, args: argparse.Namespace) -> Profile:
    roles = {role.name for role in ROLES}
    role_models = _parse_role_assignments(args.role_model, option="--role-model", allowed=roles)
    reasoning = _parse_role_assignments(args.reasoning, option="--reasoning", allowed=roles)
    if role_models and profile.inherit_model:
        raise UsageError("inherited 档案不能使用 --role-model")
    if any(not model.isprintable() or len(model) > 128 for model in role_models.values()):
        raise UsageError("--role-model 的模型名必须为 1 到 128 个可打印字符")
    if any(effort not in {"low", "medium", "high"} for effort in reasoning.values()):
        raise UsageError("--reasoning 仅支持 low、medium 或 high")
    merged_models = dict(profile.role_models)
    merged_models.update(role_models)
    merged_reasoning = default_reasoning()
    merged_reasoning.update(profile.reasoning)
    merged_reasoning.update(reasoning)
    return Profile(profile.name, profile.inherit_model, profile.models, merged_models, merged_reasoning)


def _imported_profile(path: Path) -> Profile:
    config = import_profile_config(path)
    name, models = config.profile, config.models
    if models and set(models) != {"strong", "balanced", "economy"}:
        raise ConfigError("导入档案的模型映射必须完整")
    return Profile(name, not models, models, config.role_models, config.reasoning)


def _print_changes(changes: ChangeSet) -> None:
    print(
        "完成："
        f"新增 {len(changes.created)}，更新 {len(changes.updated)}，"
        f"移除 {len(changes.removed)}，未变更 {len(changes.unchanged)}。"
    )


def _print_upgrade_changes(changes: ChangeSet, *, dry_run: bool) -> None:
    if changes.migration_from_schema is not None:
        print(f"升级预览：schema v{changes.migration_from_schema} → v{changes.migration_to_schema}")
        print(f"模型映射：保留 {changes.migration_models}")
        count = changes.migration_role_models or 0
        print(f"角色模型覆盖：保留 {count} 项")
        effort = "；".join(
            f"{role} {value} → {value}"
            for role, value in sorted(changes.migration_reasoning.items())
        )
        print(f"推理强度：{effort}")
        if dry_run:
            print("迁移备份：不会创建（dry-run）")
        elif changes.backup_path is not None:
            print(f"迁移备份：{changes.backup_path}")
    _print_changes(changes)


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


def _print_status(report: StatusReport) -> None:
    hashes = (
        "不可用"
        if report.role_hashes_match is None
        else ("匹配" if report.role_hashes_match else "不匹配")
    )
    template = report.installed_template_version or "未安装"
    print(f"插件版本：{report.plugin_version}")
    print(f"当前模式：{report.mode}")
    print(f"增强状态：{report.enhancement_state}")
    print(f"角色文件：{report.role_files_present}/{report.role_files_expected}")
    print(f"角色哈希：{hashes}")
    print(f"模型映射：{report.model_mapping_status}")
    print(f"模板版本：{template}")
    if report.reasoning_matches is False:
        print("推理强度：与配置不一致")
    print("角色身份：未验证")
    print("模型身份：未验证")
    if report.mode == "core":
        print("说明：core 仅表示本地六角色增强缺失，不证明插件已安装或启用。")


def _number(value: int | None) -> str:
    return "不可用" if value is None else f"{value:,}"


def _print_usage(summary: UsageSummary) -> None:
    scope = f"最近 {summary.range_days} 天"
    if summary.project:
        scope += f" · {summary.project}"
    print("来源：CodexBar（本地统计，成本为估算）")
    print(f"范围：{scope}")
    print(f"总 token：{_number(summary.tokens.total)}")
    print(
        f"输入：{_number(summary.tokens.input)} · "
        f"输出：{_number(summary.tokens.output)} · "
        f"缓存读取：{_number(summary.tokens.cache_read)} · "
        f"缓存创建：{_number(summary.tokens.cache_creation)}"
    )
    if summary.estimated_cost is None or summary.currency is None:
        print("估算成本：不可用")
    else:
        print(f"估算成本：{summary.currency} {summary.estimated_cost:.2f}")
    if summary.models:
        models = []
        for model in summary.models:
            tokens = _number(model.total_tokens)
            cost = "不可用" if model.estimated_cost is None else f"{model.estimated_cost:.2f}"
            models.append(f"{model.name} {tokens} token / 估算成本 {cost}")
        print("模型：" + "；".join(models))
    else:
        print("模型：不可用")
    print("角色归因：不可用")


def _run(args: argparse.Namespace) -> int:
    context = _context(args.codex_home)
    if args.command == "install":
        _print_changes(install(context, _with_overrides(_load_bundled_profile(args.profile), args), args.force))
        return SUCCESS
    if args.command == "configure":
        _print_changes(
            install(
                context,
                _with_overrides(_custom_profile(args), args),
                args.force,
                reconfigure_v1=True,
            )
        )
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
    if args.command == "status":
        report = inspect_status(context)
        if args.format == "json":
            print(json.dumps(status_to_dict(report), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            _print_status(report)
        return report.exit_code
    if args.command == "upgrade":
        changes = plan_upgrade(context, args.force) if args.dry_run else upgrade(context, args.force)
        if changes.conflicts:
            paths = ", ".join(str(path) for path in changes.conflicts)
            raise ConflictError(f"unmanaged paths: {paths}")
        _print_upgrade_changes(changes, dry_run=args.dry_run)
        return SUCCESS
    if args.command == "export-profile":
        export_profile(_safe_managed_config(context), args.path)
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
    if args.command == "enable-global-routing":
        _print_changes(enable_global_routing(context.codex_home / "AGENTS.md"))
        return SUCCESS
    if args.command == "disable-global-routing":
        _print_changes(disable_global_routing(context.codex_home / "AGENTS.md"))
        return SUCCESS
    if args.command == "usage":
        binary = discover_codexbar(args.codexbar_bin)
        check_codexbar_version(binary)
        payload = fetch_usage(binary, days=args.days)
        summary = summarize_usage(payload, project=args.project, days=args.days)
        if args.format == "json":
            print(json.dumps(usage_to_dict(summary), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            _print_usage(summary)
        return SUCCESS
    raise UsageError("未知命令")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return a stable process exit code."""
    _configure_stdio()
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
    except UsageDataError as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return ENVIRONMENT_FAILURE
    except (ConfigError, OSError, ValueError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return ENVIRONMENT_FAILURE
