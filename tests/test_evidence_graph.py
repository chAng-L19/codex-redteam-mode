from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest


CODEX_ROOT = Path(__file__).resolve().parents[1] / "codex"
if str(CODEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CODEX_ROOT))

from runtime import DurableStore, EvidenceGraph, GoalCompiler, OperationState, WorkflowRegistry


def test_evidence_graph_preserves_duplicate_identity_and_tool_provenance(tmp_path: Path) -> None:
    goal = GoalCompiler().compile("Validate SQL injection on https://target.invalid")
    workflow = WorkflowRegistry().match(goal)
    state = OperationState.create(session_id="evidence-test", goal=goal, workflow=workflow)
    store = DurableStore(tmp_path / "operations")
    store.create_operation(state, event={"source": "pytest"})
    graph = EvidenceGraph(store, tmp_path / "artifacts")
    action = workflow.actions[0]

    first = graph.add(
        run_id=state.run_id,
        action_id=action.action_id,
        artifact_type=action.expected_artifact,
        target=goal.targets[0],
        tool="pytest:adapter",
        payload={"status": "verified"},
        parent_ids=(),
        verifier=action.verifier,
        confidence=0.9,
    )
    time.sleep(1.1)
    duplicate = graph.add(
        run_id=state.run_id,
        action_id=action.action_id,
        artifact_type=action.expected_artifact,
        target=goal.targets[0],
        tool="pytest:adapter",
        payload={"status": "verified"},
        parent_ids=(),
        verifier=action.verifier,
        confidence=0.9,
    )

    assert duplicate == first
    assert graph.list(state.run_id) == (first,)

    alternate_tool = graph.add(
        run_id=state.run_id,
        action_id=action.action_id,
        artifact_type=action.expected_artifact,
        target=goal.targets[0],
        tool="pytest:alternate",
        payload={"status": "verified"},
        parent_ids=(),
        verifier=action.verifier,
        confidence=0.9,
    )

    assert alternate_tool.tool == "pytest:alternate"
    assert alternate_tool.evidence_id != first.evidence_id
    assert {node.evidence_id for node in graph.list(state.run_id)} == {
        first.evidence_id,
        alternate_tool.evidence_id,
    }

    with pytest.raises(ValueError, match="evidence_parent_missing"):
        graph.add(
            run_id=state.run_id,
            action_id=action.action_id,
            artifact_type=action.expected_artifact,
            target=goal.targets[0],
            tool="pytest:adapter",
            payload={"status": "new"},
            parent_ids=("missing-parent",),
            verifier=action.verifier,
            confidence=1.0,
        )
