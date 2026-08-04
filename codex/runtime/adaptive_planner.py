from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from .models import GoalContract, WorkflowSpec
from .workflow_registry import WorkflowRegistry


class AdaptivePlanner:
    def __init__(self, *, max_hypothesis_branches: int = 4) -> None:
        self.max_hypothesis_branches = max(1, min(8, int(max_hypothesis_branches)))

    def plan(self, goal: GoalContract, registry: WorkflowRegistry) -> WorkflowSpec:
        return registry.match(goal)

    def expand_hypotheses(
        self,
        workflow: WorkflowSpec,
        *,
        hypothesis_action_id: str,
        hypotheses: Sequence[Mapping[str, Any]],
        max_branches: int | None = None,
    ) -> tuple[WorkflowSpec, tuple[str, ...]]:
        branch_limit = self.max_hypothesis_branches if max_branches is None else max(1, int(max_branches))
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        selected = tuple(
            sorted(
                (item for item in hypotheses if isinstance(item, Mapping)),
                key=lambda item: (
                    priority_rank.get(str(item.get("priority") or "").casefold(), 4),
                    str(item.get("id") or ""),
                ),
            )[:branch_limit]
        )
        if not selected:
            return workflow, ()
        direct_validations = tuple(
            action
            for action in workflow.actions
            if hypothesis_action_id in action.depends_on and action.expected_artifact == "reproduction_artifact"
        )
        if not direct_validations:
            return workflow, ()

        actions = list(workflow.actions)
        added_ids: list[str] = []
        report_dependencies: list[str] = []
        for validation in direct_validations:
            validation_index = next(index for index, action in enumerate(actions) if action.action_id == validation.action_id)
            actions[validation_index] = replace(
                validation,
                parameters={**dict(validation.parameters), "hypothesis": dict(selected[0])},
            )
            if len(selected) == 1:
                continue

            branch_ids = {validation.action_id}
            changed = True
            while changed:
                changed = False
                for candidate in workflow.actions:
                    if candidate.expected_artifact == "final_report" or candidate.action_id in branch_ids:
                        continue
                    if any(dependency in branch_ids for dependency in candidate.depends_on):
                        branch_ids.add(candidate.action_id)
                        changed = True
            branch_actions = tuple(action for action in workflow.actions if action.action_id in branch_ids)
            terminal_ids = {
                action.action_id
                for action in branch_actions
                if not any(action.action_id in candidate.depends_on for candidate in branch_actions)
            }
            for branch_index, hypothesis in enumerate(selected[1:], start=2):
                suffix = f"--h{branch_index}"
                id_map = {action.action_id: f"{action.action_id}{suffix}" for action in branch_actions}
                for action in branch_actions:
                    cloned = replace(
                        action,
                        action_id=id_map[action.action_id],
                        name=f"{action.name} [hypothesis {branch_index}]",
                        depends_on=tuple(id_map.get(item, item) for item in action.depends_on),
                        rollback_action=id_map.get(action.rollback_action, action.rollback_action),
                        parameters={**dict(action.parameters), "hypothesis": dict(hypothesis)},
                        attack_tags=tuple(dict.fromkeys((*action.attack_tags, str(hypothesis.get("id") or suffix)))),
                    )
                    actions.append(cloned)
                    added_ids.append(cloned.action_id)
                report_dependencies.extend(id_map[item] for item in terminal_ids)

        if report_dependencies:
            actions = [
                replace(action, depends_on=tuple(dict.fromkeys((*action.depends_on, *report_dependencies))))
                if action.expected_artifact == "final_report"
                else action
                for action in actions
            ]
        if not added_ids and actions == list(workflow.actions):
            return workflow, ()
        expanded = replace(workflow, actions=tuple(actions))
        return expanded, tuple(added_ids)
