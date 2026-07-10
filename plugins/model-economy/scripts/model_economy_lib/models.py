from dataclasses import dataclass
from typing import Literal, Mapping


Capability = Literal["strong", "balanced", "economy"]


@dataclass(frozen=True)
class RoleSpec:
    name: str
    capability: Capability
    reasoning_effort: Literal["low", "medium", "high"]
    sandbox_mode: Literal["read-only", "workspace-write"]
    description: str
    developer_instructions: str


@dataclass(frozen=True)
class Profile:
    name: str
    inherit_model: bool
    models: Mapping[Capability, str]


ROLES = (
    RoleSpec(
        name="model-economy-architect",
        capability="strong",
        reasoning_effort="high",
        sandbox_mode="read-only",
        description="架构与疑难决策角色",
        developer_instructions="只读分析系统设计与棘手问题，给出清晰建议。不得递归委派。",
    ),
    RoleSpec(
        name="model-economy-final-reviewer",
        capability="strong",
        reasoning_effort="high",
        sandbox_mode="read-only",
        description="最终质量与风险审查角色",
        developer_instructions="只读审查变更、风险与验证证据，报告明确结论。不得递归委派。",
    ),
    RoleSpec(
        name="model-economy-implementer",
        capability="balanced",
        reasoning_effort="high",
        sandbox_mode="workspace-write",
        description="功能实现角色",
        developer_instructions="实现已明确的任务并验证结果。只修改任务明确拥有的文件。不得递归委派。",
    ),
    RoleSpec(
        name="model-economy-reviewer",
        capability="balanced",
        reasoning_effort="medium",
        sandbox_mode="read-only",
        description="代码审查角色",
        developer_instructions="只读检查正确性、回归风险与测试缺口。不得递归委派。",
    ),
    RoleSpec(
        name="model-economy-explorer",
        capability="economy",
        reasoning_effort="medium",
        sandbox_mode="read-only",
        description="代码库探索角色",
        developer_instructions="只读定位相关代码和约束，简洁汇报发现。不得递归委派。",
    ),
    RoleSpec(
        name="model-economy-batch-worker",
        capability="economy",
        reasoning_effort="low",
        sandbox_mode="workspace-write",
        description="独立批量任务角色",
        developer_instructions="完成边界明确的独立任务。只修改任务明确拥有的文件。不得递归委派。",
    ),
)
