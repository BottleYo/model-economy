import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "plugins/model-economy/skills/cost-aware-development"
SKILL = SKILL_DIR / "SKILL.md"
POLICY = SKILL_DIR / "references/routing-policy.json"
ROLE_MATRIX = SKILL_DIR / "references/role-matrix.md"
ROUTING_EXAMPLES = SKILL_DIR / "references/routing-examples.md"
CONTEXT_CONTRACT = SKILL_DIR / "references/context-contract.md"
QUALITY_GATES = SKILL_DIR / "references/quality-gates.md"


def load_policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def parse_markdown_table(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    wanted = list(header)

    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells != wanted:
            continue
        rows = []
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            values = [value.strip() for value in row.strip().strip("|").split("|")]
            if len(values) != len(wanted):
                raise AssertionError(f"invalid table row in {path}: {row}")
            rows.append(dict(zip(wanted, values, strict=True)))
        return rows

    raise AssertionError(f"missing table {header!r} in {path}")


def role_names(entries):
    return {
        entry if isinstance(entry, str) else entry["role"]
        for entry in entries
    }


def parse_role_set(value: str) -> set[str]:
    if value == "—":
        return set()
    return {item.strip() for item in value.split("；")}


def classify(policy, facts):
    if policy["match_semantics"] != "first_match":
        raise AssertionError("unsupported match semantics")

    for class_id in policy["classification_order"]:
        rule = policy["task_classes"][class_id]["match"]
        operator = rule["operator"]
        predicates = rule["predicates"]
        if operator == "any" and any(facts.get(name, False) for name in predicates):
            return class_id
        if operator == "all" and all(facts.get(name, False) for name in predicates):
            return class_id
        if operator == "default":
            return class_id

    raise AssertionError("classification produced no result")


class SkillContractTests(unittest.TestCase):
    def test_policy_has_ordered_first_match_classification_and_default_fallback(self):
        policy = load_policy()

        self.assertEqual(policy["schema_version"], 4)
        self.assertEqual(
            policy["classification_order"],
            ["large_or_high_risk", "mechanical", "simple", "standard"],
        )
        self.assertEqual(policy["match_semantics"], "first_match")
        self.assertEqual(set(policy["task_classes"]), set(policy["classification_order"]))
        for class_id in policy["classification_order"]:
            self.assertEqual(
                set(policy["task_classes"][class_id]),
                {
                    "label",
                    "match",
                    "primary_execution",
                    "base_allowed_roles",
                    "conditional_roles",
                    "required_roles",
                    "forbidden_roles",
                    "strong_max",
                },
            )

        standard = policy["task_classes"]["standard"]
        self.assertEqual(standard["match"], {"operator": "default", "predicates": []})
        self.assertEqual(policy["classification_order"][-1], "standard")
        self.assertEqual(classify(policy, {}), "standard")

    def test_classification_rules_are_independently_decidable_and_first_match_wins(self):
        policy = load_policy()
        classes = policy["task_classes"]
        economy_ids = [condition["id"] for condition in policy["economy_conditions"]]

        self.assertEqual(
            classes["large_or_high_risk"]["match"],
            {
                "operator": "any",
                "predicates": ["high_risk", "new_architecture", "wide_blast_radius"],
            },
        )
        self.assertEqual(
            classes["mechanical"]["match"],
            {"operator": "all", "predicates": economy_ids},
        )
        self.assertEqual(
            classes["simple"]["match"],
            {
                "operator": "all",
                "predicates": [
                    "known_files",
                    "no_open_judgment",
                    "directly_verifiable",
                    "not_creative_or_behavioral_change",
                ],
            },
        )

        for predicate in classes["large_or_high_risk"]["match"]["predicates"]:
            self.assertEqual(classify(policy, {predicate: True}), "large_or_high_risk")

        mechanical_facts = dict.fromkeys(economy_ids, True)
        simple_facts = dict.fromkeys(classes["simple"]["match"]["predicates"], True)
        self.assertEqual(classify(policy, mechanical_facts), "mechanical")
        self.assertEqual(classify(policy, simple_facts), "simple")
        self.assertEqual(
            classify(policy, {**mechanical_facts, **simple_facts}), "mechanical"
        )
        self.assertEqual(
            classify(policy, {**mechanical_facts, **simple_facts, "high_risk": True}),
            "large_or_high_risk",
        )
        incomplete_simple = {**simple_facts, "no_open_judgment": False}
        self.assertEqual(classify(policy, incomplete_simple), "standard")

    def test_each_class_partitions_all_six_roles_and_declares_strong_max(self):
        policy = load_policy()
        all_roles = set(policy["roles"])
        expected = {
            "large_or_high_risk": {
                "base": {"model-economy-implementer", "model-economy-explorer"},
                "conditional": set(),
                "required": {
                    "model-economy-architect",
                    "model-economy-final-reviewer",
                },
                "forbidden": {
                    "model-economy-reviewer",
                    "model-economy-batch-worker",
                },
                "strong_max": 2,
            },
            "mechanical": {
                "base": {"model-economy-batch-worker"},
                "conditional": set(),
                "required": set(),
                "forbidden": all_roles - {"model-economy-batch-worker"},
                "strong_max": 0,
            },
            "simple": {
                "base": set(),
                "conditional": set(),
                "required": set(),
                "forbidden": all_roles,
                "strong_max": 0,
            },
            "standard": {
                "base": {"model-economy-implementer"},
                "conditional": {
                    "model-economy-architect",
                    "model-economy-reviewer",
                    "model-economy-explorer",
                },
                "required": set(),
                "forbidden": {
                    "model-economy-final-reviewer",
                    "model-economy-batch-worker",
                },
                "strong_max": 1,
            },
        }

        for class_id, class_policy in policy["task_classes"].items():
            actual = {
                "base": set(class_policy["base_allowed_roles"]),
                "conditional": role_names(class_policy["conditional_roles"]),
                "required": role_names(class_policy["required_roles"]),
                "forbidden": set(class_policy["forbidden_roles"]),
                "strong_max": class_policy["strong_max"],
            }
            self.assertEqual(actual, expected[class_id])
            groups = [
                actual["base"],
                actual["conditional"],
                actual["required"],
                actual["forbidden"],
            ]
            self.assertEqual(set().union(*groups), all_roles)
            self.assertEqual(sum(map(len, groups)), len(all_roles))

    def test_standard_architect_is_conditional_after_two_failures(self):
        standard = load_policy()["task_classes"]["standard"]

        self.assertNotIn("model-economy-architect", standard["base_allowed_roles"])
        architect = next(
            entry
            for entry in standard["conditional_roles"]
            if entry["role"] == "model-economy-architect"
        )
        self.assertEqual(architect["when"], {"failed_attempts": {"gte": 2}})
        self.assertEqual(architect["max_calls"], 1)
        self.assertEqual(architect["output"], "diagnostic_decision")
        self.assertEqual(
            architect["after_completion"],
            {
                "implementation_capability": "balanced",
                "reclassify_when": "large_or_high_risk_discovered",
                "counts_as_large_architect_when": [
                    "before_new_design_approval",
                    "large_architect_output_contract_satisfied",
                ],
            },
        )

    def test_standard_optional_roles_have_machine_readable_conditions(self):
        standard = load_policy()["task_classes"]["standard"]
        conditional = {entry["role"]: entry for entry in standard["conditional_roles"]}

        self.assertEqual(
            conditional["model-economy-explorer"]["when"],
            {
                "operator": "any",
                "predicates": [
                    "file_location_uncertain",
                    "dependency_relationship_uncertain",
                    "existing_facts_uncertain",
                ],
            },
        )
        self.assertEqual(
            conditional["model-economy-reviewer"]["when"],
            {
                "operator": "any",
                "predicates": [
                    "cross_module_change",
                    "critical_logic_change",
                    "non_obvious_regression_risk",
                    "material_test_coverage_doubt",
                ],
            },
        )

    def test_primary_execution_is_exactly_one_and_machine_readable(self):
        classes = load_policy()["task_classes"]

        self.assertEqual(
            classes["standard"]["primary_execution"],
            {
                "selection": "exactly_one",
                "choices": ["main_agent", "model-economy-implementer"],
            },
        )
        self.assertEqual(
            classes["large_or_high_risk"]["primary_execution"],
            {
                "selection": "exactly_one",
                "choices": ["main_agent", "model-economy-implementer"],
            },
        )
        self.assertEqual(classes["simple"]["primary_execution"]["choices"], ["main_agent"])
        self.assertEqual(
            classes["mechanical"]["primary_execution"]["choices"],
            ["model-economy-batch-worker"],
        )

    def test_large_required_roles_are_completion_gates(self):
        large = load_policy()["task_classes"]["large_or_high_risk"]

        self.assertEqual(
            large["required_roles"],
            [
                {
                    "role": "model-economy-architect",
                    "when": "before_design_approval",
                    "must_complete_before": "design_approval",
                },
                {
                    "role": "model-economy-final-reviewer",
                    "when": "after_verification",
                    "must_complete_before": "task_completion",
                },
            ],
        )
        self.assertEqual(large["strong_max"], 2)

    def test_approval_gate_blocks_ambiguous_or_high_risk_work_without_evidence(self):
        gate = load_policy()["approval_gate"]

        self.assertEqual(
            set(gate["required_when"]),
            {
                "material_ambiguity",
                "materially_different_outcomes",
                "high_risk_decision",
                "unapproved_architecture_boundary",
            },
        )
        self.assertEqual(
            gate["required_evidence"], ["approved_design", "approval_evidence"]
        )
        self.assertEqual(gate["forbidden_without_evidence"], ["implementation"])
        self.assertEqual(
            set(gate["not_repeated_when"]),
            {
                "clear_goal_constraints_and_acceptance",
                "reproducible_bugfix",
                "implementation_within_approved_design",
                "literal_change",
                "deterministic_mechanical_change",
            },
        )

    def test_machine_policy_declares_four_native_quality_gates(self):
        self.assertEqual(
            load_policy()["quality_gates"],
            {
                "intent": "conditional_before_implementation",
                "planning": "scaled_by_task_class",
                "testing": "scaled_by_behavioral_risk",
                "evidence": "required_before_completion_claim",
            },
        )

    def test_machine_policy_makes_strict_handoff_mutually_exclusive(self):
        modes = load_policy()["orchestration_modes"]

        self.assertEqual(modes["default"], "model_economy")
        self.assertEqual(modes["selection_scope"], "current_task_only")
        native = modes["modes"]["model_economy"]
        strict = modes["modes"]["superpowers_strict"]
        self.assertTrue(native["task_class_policy_applies"])
        self.assertTrue(native["native_quality_gates_apply"])
        self.assertEqual(native["model_economy_roles"], "per_task_class")
        self.assertEqual(strict["trigger"]["operator"], "explicit_user_request")
        self.assertIn("full Superpowers", strict["trigger"]["phrases"])
        self.assertFalse(strict["task_class_policy_applies"])
        self.assertFalse(strict["native_quality_gates_apply"])
        self.assertEqual(strict["model_economy_roles"], "forbidden")
        self.assertEqual(strict["model_economy_scope"], ["model_advice", "cost_advice"])

    def test_economy_work_requires_all_five_machine_checkable_conditions(self):
        conditions = load_policy()["economy_conditions"]

        self.assertEqual(len(conditions), 5)
        self.assertEqual(
            {condition["id"] for condition in conditions},
            {
                "deterministic_input_targets_and_rules",
                "independent_retryable_operations",
                "no_sensitive_or_high_risk_boundary",
                "automated_check_per_result",
                "bounded_explicit_failure",
            },
        )
        self.assertTrue(all(condition["required"] for condition in conditions))

    def test_six_role_permissions_and_strong_architect_boundary_are_structured(self):
        roles = load_policy()["roles"]

        self.assertEqual(
            set(roles),
            {
                "model-economy-architect",
                "model-economy-final-reviewer",
                "model-economy-implementer",
                "model-economy-reviewer",
                "model-economy-explorer",
                "model-economy-batch-worker",
            },
        )
        architect = roles["model-economy-architect"]
        self.assertEqual(architect["capability"], "strong")
        self.assertEqual(
            architect["allowed_outputs"],
            ["architecture_boundaries", "risks", "decisions"],
        )
        self.assertEqual(architect["forbidden_outputs"], ["plans", "patches", "code"])
        self.assertEqual(architect["write_access"], "read_only")

    def test_context_contract_redacts_sensitive_and_irrelevant_delegation_context(self):
        sanitization = load_policy()["context_sanitization"]

        self.assertEqual(
            set(sanitization["remove_before_sending"]),
            {
                "secrets",
                "tokens",
                "personal_data",
                "production_data",
                "internal_urls",
                "irrelevant_paths",
            },
        )
        self.assertEqual(sanitization["placeholder_format"], "[REDACTED_<TYPE>]")
        self.assertIn("## 脱敏规则", CONTEXT_CONTRACT.read_text(encoding="utf-8"))

    def test_delegated_write_sets_are_mutually_exclusive_or_serialized_by_the_main_agent(self):
        write_sets = load_policy()["delegation"]["write_file_sets"]

        self.assertTrue(write_sets["must_be_mutually_exclusive"])
        self.assertEqual(write_sets["overlap_handling"], "main_agent_serializes")

    def test_subagent_budget_counts_total_starts_and_survives_reclassification(self):
        delegation = load_policy()["delegation"]

        self.assertEqual(delegation["max_subagent_starts_per_task"], 3)
        self.assertEqual(delegation["max_concurrent_subagents"], 3)
        self.assertFalse(delegation["reclassification_resets_budget"])
        self.assertEqual(delegation["recursive_delegation"], "forbidden")

    def test_skill_defines_single_orchestration_authority_and_evidence_layers(self):
        skill = SKILL.read_text(encoding="utf-8")
        context = CONTEXT_CONTRACT.read_text(encoding="utf-8")

        self.assertIn("按指令优先级只选择一套代理编排", skill)
        self.assertIn("subagent-driven-development", skill)
        self.assertIn("不得增加所选路由之外", skill)
        self.assertIn("主 agent 或一个 `model-economy-implementer`", skill)
        self.assertIn("变更评估", skill)
        self.assertIn("残余交付风险", skill)
        self.assertIn("新鲜验证证据", skill)
        self.assertIn("非目标：", context)
        self.assertIn("验证命令：", context)
        self.assertIn("实际启动：未记录", context)
        self.assertIn("模型身份：未验证", context)

    def test_native_quality_kernel_has_no_superpowers_skill_dependency(self):
        skill = SKILL.read_text(encoding="utf-8")

        self.assertNotIn("superpowers:", skill.lower())
        self.assertIn("原生质量内核", skill)
        self.assertIn("references/quality-gates.md", skill)

    def test_quality_gates_are_risk_adaptive_and_complete(self):
        quality = QUALITY_GATES.read_text(encoding="utf-8")

        for gate in ("意图门", "计划门", "测试门", "证据门"):
            self.assertIn(f"## {gate}", quality)
        self.assertIn("简单任务", quality)
        self.assertIn("不写持久化计划", quality)
        self.assertIn("缺陷修复", quality)
        self.assertIn("新鲜验证证据", quality)
        self.assertIn("无法验证", quality)

    def test_superpowers_strict_requires_explicit_current_task_authorization(self):
        skill = SKILL.read_text(encoding="utf-8")

        self.assertIn("安装、启用或发现 Superpowers 不构成", skill)
        self.assertIn("当前任务", skill)
        self.assertIn("完整 Superpowers", skill)
        self.assertIn("full Superpowers", skill)
        self.assertIn("只提供模型与成本建议", skill)
        self.assertIn("不得启动 Model Economy 角色", skill)

    def test_role_matrix_matches_policy_capabilities(self):
        policy = load_policy()
        role_rows = parse_markdown_table(
            ROLE_MATRIX, ("角色", "能力", "何时使用", "输出边界")
        )
        roles_from_matrix = {
            row["角色"].strip("`"): row["能力"].replace("`", "").split("，")[0]
            for row in role_rows
        }
        self.assertEqual(
            roles_from_matrix,
            {name: role["capability"] for name, role in policy["roles"].items()},
        )

    def test_every_routing_example_matches_all_policy_role_sets_and_strong_max(self):
        policy = load_policy()
        rows = parse_markdown_table(
            ROUTING_EXAMPLES,
            (
                "场景",
                "分类 ID",
                "基础允许角色",
                "条件角色",
                "必需角色",
                "禁止角色",
                "`strong` 上限",
            ),
        )
        expected_scenarios = {
            "高风险安全迁移": "large_or_high_risk",
            "引入新架构": "large_or_high_risk",
            "广泛爆炸半径": "large_or_high_risk",
            "已批准规格内的批量改名": "mechanical",
            "已知文件的纯字面修正": "simple",
            "跨模块、边界明确的低风险功能": "standard",
            "标准任务两次实质失败": "standard",
        }
        self.assertEqual({row["场景"]: row["分类 ID"] for row in rows}, expected_scenarios)

        for row in rows:
            class_policy = policy["task_classes"][row["分类 ID"]]
            self.assertEqual(
                parse_role_set(row["基础允许角色"]),
                set(class_policy["base_allowed_roles"]),
            )
            self.assertEqual(
                parse_role_set(row["条件角色"]),
                role_names(class_policy["conditional_roles"]),
            )
            self.assertEqual(
                parse_role_set(row["必需角色"]),
                role_names(class_policy["required_roles"]),
            )
            self.assertEqual(
                parse_role_set(row["禁止角色"]),
                set(class_policy["forbidden_roles"]),
            )
            self.assertEqual(int(row["`strong` 上限"]), class_policy["strong_max"])

        self.assertIn("references/routing-policy.json", SKILL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
