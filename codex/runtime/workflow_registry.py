from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Iterable

from .models import GoalContract, WorkflowSpec


IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class WorkflowRegistry:
    """Load and validate the single durable workflow."""

    def __init__(self, roots: Iterable[Path] | None = None) -> None:
        default_root = Path(__file__).resolve().parent.parent / "workflows"
        self.roots = tuple(roots or (default_root,))
        self._workflow: WorkflowSpec | None = None

    def load(self, *, refresh: bool = False) -> tuple[WorkflowSpec, ...]:
        if self._workflow is not None and not refresh:
            return (self._workflow,)
        candidates = [root / "generic-adaptive.toml" for root in self.roots if root.is_dir()]
        path = next((item for item in candidates if item.is_file()), None)
        if path is None:
            raise ValueError("generic_workflow_missing")
        workflow = WorkflowSpec.from_dict(tomllib.loads(path.read_text(encoding="utf-8-sig")))
        self._validate(workflow, path)
        self._workflow = workflow
        return (workflow,)

    def _validate(self, workflow: WorkflowSpec, path: Path) -> None:
        if workflow.workflow_id != "generic-adaptive":
            raise ValueError(f"workflow_id_invalid:{workflow.workflow_id or path}")
        if not workflow.actions:
            raise ValueError("workflow_actions_missing:generic-adaptive")
        action_ids = [action.action_id for action in workflow.actions]
        if any(not IDENTIFIER_RE.fullmatch(action_id) for action_id in action_ids):
            raise ValueError("workflow_action_id_invalid:generic-adaptive")
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("workflow_duplicate_action:generic-adaptive")
        known = set(action_ids)
        for action in workflow.actions:
            if not action.required_capabilities or not action.expected_artifact:
                raise ValueError(f"workflow_action_incomplete:{action.action_id}")
            unknown = set(action.depends_on) - known
            if unknown:
                raise ValueError(f"workflow_unknown_dependency:{action.action_id}:{sorted(unknown)}")
        remaining = set(action_ids)
        dependencies = {action.action_id: set(action.depends_on) for action in workflow.actions}
        while remaining:
            ready = {action_id for action_id in remaining if not (dependencies[action_id] & remaining)}
            if not ready:
                raise ValueError("workflow_dependency_cycle:generic-adaptive")
            remaining -= ready

    def get(self, workflow_id: str = "generic-adaptive") -> WorkflowSpec:
        workflow = self.load()[0]
        if workflow_id != workflow.workflow_id:
            raise KeyError(f"workflow_not_found:{workflow_id}")
        return workflow

    def match(self, goal: GoalContract) -> WorkflowSpec:
        del goal
        return self.get()

    def match_many(self, goal: GoalContract, *, limit: int = 1) -> tuple[WorkflowSpec, ...]:
        del goal, limit
        return (self.get(),)
