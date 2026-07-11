import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_public_documents_are_bilingual_and_link_to_each_other(self):
        document_pairs = (
            ("README.md", "README.zh-CN.md"),
            ("SECURITY.md", "SECURITY.zh-CN.md"),
            ("CHANGELOG.md", "CHANGELOG.zh-CN.md"),
            ("docs/en/installation.md", "docs/zh-CN/installation.md"),
            ("docs/en/how-it-works.md", "docs/zh-CN/how-it-works.md"),
            ("docs/en/cli-reference.md", "docs/zh-CN/cli-reference.md"),
        )

        for english_path, chinese_path in document_pairs:
            with self.subTest(english_path=english_path):
                english = (ROOT / english_path).read_text(encoding="utf-8")
                chinese = (ROOT / chinese_path).read_text(encoding="utf-8")
                if english_path.startswith("docs/"):
                    english_target = "../zh-CN/" + Path(chinese_path).name
                    chinese_target = "../en/" + Path(english_path).name
                else:
                    english_target = chinese_path
                    chinese_target = english_path
                self.assertIn(english_target, english)
                self.assertIn(chinese_target, chinese)

    def test_readmes_share_the_public_information_architecture(self):
        expected_sections = (
            "How it works",
            "Install in 60 seconds",
            "Task classification",
            "Roles",
            "Global routing",
            "Security and trust boundaries",
            "Documentation",
            "Current limitations",
            "Contributing",
            "License",
        )
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("assets/social-preview.png", english)
        self.assertIn("assets/social-preview.png", chinese)
        self.assertIn("assets/model-economy-flow-en.svg", english)
        self.assertIn("assets/model-economy-flow-zh-CN.svg", chinese)
        self.assertIn("Use strong models for decisions, not routine work.", english)
        self.assertIn("让强模型负责关键判断，而不是日常机械工作", chinese)

        last_index = -1
        for section in expected_sections:
            index = english.index(section)
            self.assertGreater(index, last_index)
            last_index = index

        for section in (
            "工作原理",
            "60 秒安装",
            "任务分类",
            "角色",
            "全局路由",
            "安全与信任边界",
            "文档",
            "当前限制",
            "贡献",
            "许可证",
        ):
            self.assertIn(section, chinese)

    def test_each_bilingual_command_document_matches_cli_help(self):
        cli = ROOT / "plugins/model-economy/scripts/model_economy.py"
        help_output = subprocess.run(
            [sys.executable, str(cli), "--help"],
            check=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout
        command_sets = {
            ("README.md", "README.zh-CN.md"): (
                "install",
                "configure",
                "verify",
                "enable-global-routing",
                "disable-global-routing",
            ),
            ("docs/en/installation.md", "docs/zh-CN/installation.md"): (
                "install",
                "configure",
                "verify",
                "doctor",
                "upgrade",
                "export-profile",
                "import-profile",
                "uninstall",
                "enable-global-routing",
                "disable-global-routing",
            ),
            ("docs/en/cli-reference.md", "docs/zh-CN/cli-reference.md"): (
                "install",
                "configure",
                "verify",
                "doctor",
                "upgrade",
                "export-profile",
                "import-profile",
                "uninstall",
                "enable-global-routing",
                "disable-global-routing",
            ),
        }

        for documents, commands in command_sets.items():
            for command in commands:
                self.assertIn(command, help_output)
            for document in documents:
                text = (ROOT / document).read_text(encoding="utf-8")
                with self.subTest(document=document):
                    for command in commands:
                        self.assertIn(f"model_economy.py {command}", text)

    def test_public_docs_do_not_make_unverified_claims(self):
        for document in (
            "README.md",
            "README.zh-CN.md",
            "docs/en/installation.md",
            "docs/zh-CN/installation.md",
            "docs/en/cli-reference.md",
            "docs/zh-CN/cli-reference.md",
        ):
            text = (ROOT / document).read_text(encoding="utf-8").lower()
            with self.subTest(document=document):
                self.assertNotIn("proven token savings", text)
                self.assertNotIn("verified model identity", text)

    def test_readme_local_images_exist(self):
        for target in (
            "assets/social-preview.png",
            "assets/model-economy-flow-en.svg",
            "assets/model-economy-flow-zh-CN.svg",
        ):
            with self.subTest(target=target):
                self.assertTrue((ROOT / target).is_file(), f"missing local image: {target}")

    def test_readmes_and_security_docs_describe_marked_agents_block(self):
        expected = {
            "README.md": "marked, managed Model Economy block",
            "README.zh-CN.md": "带标记的 Model Economy 受管理区块",
            "SECURITY.md": "marked, managed Model Economy block",
            "SECURITY.zh-CN.md": "带标记的 Model Economy 受管理区块",
        }
        for document, statement in expected.items():
            with self.subTest(document=document):
                text = (ROOT / document).read_text(encoding="utf-8")
                self.assertIn("$CODEX_HOME/AGENTS.md", text)
                self.assertIn(statement, text)

    def test_local_marketplace_upgrade_docs_use_supported_refresh_flow(self):
        commands = (
            "git pull --ff-only",
            "codex plugin remove model-economy@model-economy-public",
            "codex plugin marketplace remove model-economy-public",
            "codex plugin marketplace add .",
            "codex plugin add model-economy@model-economy-public",
            "python3 plugins/model-economy/scripts/model_economy.py upgrade --dry-run",
            "python3 plugins/model-economy/scripts/model_economy.py upgrade\n",
        )
        documents = {
            "docs/en/installation.md": "## Upgrade",
            "docs/zh-CN/installation.md": "## 升级",
        }
        for document, heading in documents.items():
            text = (ROOT / document).read_text(encoding="utf-8")
            with self.subTest(document=document):
                self.assertNotIn("codex plugin marketplace upgrade model-economy-public", text)
                section_start = text.index(heading)
                section_end = text.index("\n## ", section_start + len(heading))
                section = text[section_start:section_end]
                positions = [section.index(command) for command in commands]
                self.assertEqual(positions, sorted(positions))

    def test_fail_closed_docs_name_force_as_explicit_user_override(self):
        expected = {
            "README.md": "Only an explicit user-authorized `--force` operation overrides",
            "README.zh-CN.md": "只有用户明确授权的 `--force` 操作可以越过",
            "SECURITY.md": "Only an explicit user-authorized `--force` operation overrides",
            "SECURITY.zh-CN.md": "只有用户明确授权的 `--force` 操作可以越过",
        }
        for document, statement in expected.items():
            with self.subTest(document=document):
                text = (ROOT / document).read_text(encoding="utf-8")
                self.assertIn(statement, text)

    def test_x_promotion_drafts_are_not_tracked_as_internal_docs(self):
        for path in (
            "docs/superpowers/specs/2026-07-11-bilingual-github-design.md",
            "docs/superpowers/plans/2026-07-11-bilingual-github.md",
        ):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists(), f"remove internal promotion draft: {path}")

    def test_large_or_high_risk_docs_include_read_only_explorer(self):
        english = (ROOT / "docs/en/how-it-works.md").read_text(encoding="utf-8")
        chinese = (ROOT / "docs/zh-CN/how-it-works.md").read_text(encoding="utf-8")

        self.assertIn(
            "`explorer` provides read-only fact collection",
            english,
        )
        self.assertIn("`explorer` 负责只读事实收集", chinese)

    def test_manifest_and_marketplace_agree(self):
        manifest = json.loads(
            (ROOT / "plugins/model-economy/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "model-economy")
        self.assertEqual(marketplace["name"], "model-economy-public")
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["source"]["path"], "./plugins/model-economy")

    def test_global_routing_release_contract(self):
        manifest = json.loads(
            (ROOT / "plugins/model-economy/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/model-economy/skills/cost-aware-development/SKILL.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "0.2.0")
        self.assertIn('version = "0.2.0"', pyproject)
        self.assertIn("软件开发", skill.split("---", 2)[1])
        self.assertIn("enable-global-routing", readme)
        self.assertIn("disable-global-routing", readme)
        self.assertIn("A project's own `AGENTS.md` can override", readme)

    def test_ci_checkout_fetches_full_history(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        checkout = "      - uses: actions/checkout@v4\n"
        self.assertIn(checkout + "        with:\n          fetch-depth: 0\n", workflow)

    def test_ci_forces_utf8_on_every_platform(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn('PYTHONUTF8: "1"', workflow)

    def test_readme_custom_commands_are_single_line_for_posix_and_powershell(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        custom_start = readme.index("# 3. custom")
        custom_end = readme.index("```", custom_start)
        custom = readme[custom_start:custom_end]
        self.assertNotIn("\\\n", custom)
        self.assertIn(
            "python3 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>",
            custom,
        )
        self.assertIn(
            "py -3.11 plugins/model-economy/scripts/model_economy.py configure --strong <strong-model> --balanced <balanced-model> --economy <economy-model>",
            custom,
        )


if __name__ == "__main__":
    unittest.main()
