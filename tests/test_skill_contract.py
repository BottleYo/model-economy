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


def load_policy():
    return json.loads(POLICY.read_text())


def parse_markdown_table(path: Path, header: tuple[str, ...]) -> list[dict[str, str]]:
    lines = path.read_text().splitlines()
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

        self.assertEqual(policy["schema_version"], 2)
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
                "base": {
                    "model-economy-implementer",
                    "model-economy-reviewer",
                    "model-economy-explorer",
                },
                "conditional": {"model-economy-architect"},
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
        self.assertEqual(
            standard["conditional_roles"],
            [
                {
                    "role": "model-economy-architect",
                    "when": {"failed_attempts": {"gte": 2}},
                    "max_calls": 1,
                    "output": "diagnostic_decision",
                    "after_completion": {
                        "implementation_capability": "balanced",
                        "reclassify_when": "large_or_high_risk_discovered",
                    },
                }
            ],
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

    def test_approval_gate_blocks_creative_or_behavioral_work_without_evidence(self):
        gate = load_policy()["approval_gate"]

        self.assertEqual(gate["required_for"], ["creative_change", "behavior_change"])
        self.assertEqual(
            gate["required_evidence"], ["approved_design", "approval_evidence"]
        )
        self.assertEqual(gate["forbidden_without_evidence"], ["planning", "implementation"])
        self.assertEqual(
            set(gate["exceptions"]),
            {"literal_change", "mechanical_change_within_approved_spec"},
        )

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
        self.assertIn("## 脱敏规则", CONTEXT_CONTRACT.read_text())

    def test_delegated_write_sets_are_mutually_exclusive_or_serialized_by_the_main_agent(self):
        write_sets = load_policy()["delegation"]["write_file_sets"]

        self.assertTrue(write_sets["must_be_mutually_exclusive"])
        self.assertEqual(write_sets["overlap_handling"], "main_agent_serializes")

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

        self.assertIn("references/routing-policy.json", SKILL.read_text())


if __name__ == "__main__":
    unittest.main()
