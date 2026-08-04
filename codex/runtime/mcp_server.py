from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any, Mapping

from .operation_runtime import OperationRuntime
from .adaptive_planner import AdaptivePlanner
from .session_bridge import sync_session_summary
from .tool_broker import ToolBroker


TOOL_DEFINITIONS = [
    {
        "name": "redteam_run",
        "description": "Single autonomous entrypoint: start or resume one operation or a multi-target batch, accept Host Agent observations, and continue to the next durable or terminal state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "objective": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "workflow_hint": {"type": "string"},
                "run_id": {"type": "string"},
                "batch_session_id": {"type": "string"},
                "observation": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string"},
                        "output": {},
                        "tool": {"type": "string"},
                    },
                    "required": ["output"],
                },
                "observations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "run_id": {"type": "string"},
                            "action_id": {"type": "string"},
                            "output": {},
                            "tool": {"type": "string"},
                        },
                        "required": ["run_id", "output"],
                        "additionalProperties": False,
                    },
                },
                "starting_context": {"type": "object"},
                "constraints": {"type": "object"},
                "success_predicates": {"type": "array", "items": {"type": "object"}},
                "max_actions": {"type": "integer", "minimum": 1, "maximum": 512},
                "max_total_actions": {"type": "integer", "minimum": 1, "maximum": 4096},
                "auto_continue": {"type": "boolean"},
                "max_cycles": {"type": "integer", "minimum": 1, "maximum": 64},
                "max_retries_per_action": {"type": "integer", "minimum": 0, "maximum": 8},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_start",
        "description": "Compile a red-team goal, select a typed workflow, execute available tools, and persist the operation until its next durable state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "objective": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "workflow_hint": {"type": "string"},
                "starting_context": {"type": "object"},
                "constraints": {"type": "object"},
                "success_predicates": {"type": "array", "items": {"type": "object"}},
                "max_actions": {"type": "integer", "minimum": 1, "maximum": 512},
                "max_total_actions": {"type": "integer", "minimum": 1, "maximum": 4096},
                "max_retries_per_action": {"type": "integer", "minimum": 0, "maximum": 8},
            },
            "required": ["session_id", "objective"],
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_resume",
        "description": "Resume a persisted operation without requiring copied tool output from the user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "max_actions": {"type": "integer", "minimum": 1, "maximum": 512},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_status",
        "description": "Return operation state, verified evidence, missing predicates, and the next executable action.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_submit_observation",
        "description": "Submit host-agent tool output to the current typed action; semantic verification and lineage checks run before the workflow advances automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "action_id": {"type": "string"},
                "output": {},
                "tool": {"type": "string"},
                "continue_run": {"type": "boolean"},
            },
            "required": ["run_id", "action_id", "output"],
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_evidence",
        "description": "Fetch one verified evidence node by operation and evidence ID when its payload was omitted from a compact status response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "evidence_id": {"type": "string"},
            },
            "required": ["run_id", "evidence_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_cancel",
        "description": "Cancel an active operation, run an available cleanup action, and persist the cleanup outcome.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "batch_session_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "redteam_events",
        "description": "Return the durable event trace for an operation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "after_event_id": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
    },
]
TOOL_DEFINITIONS_BY_NAME = {str(item["name"]): item for item in TOOL_DEFINITIONS}


class RuntimeMcpServer:
    def __init__(
        self,
        runtime: OperationRuntime,
        *,
        default_max_actions: int = 64,
        default_max_retries_per_action: int = 2,
    ) -> None:
        self.runtime = runtime
        self.default_max_actions = max(1, min(512, int(default_max_actions)))
        self.default_max_retries_per_action = max(0, min(8, int(default_max_retries_per_action)))

    def _continue_summary(
        self,
        summary: Mapping[str, Any],
        *,
        cycle_actions: int,
        max_cycles: int,
        auto_continue: bool,
    ) -> dict[str, Any]:
        current = dict(summary)
        cycles = 1
        run_id = str(current.get("run_id") or "")
        while auto_continue and run_id and current.get("status") == "paused_budget" and cycles < max_cycles:
            current = self.runtime.resume(run_id, max_actions=cycle_actions).summary()
            cycles += 1
        current["automation_cycles"] = cycles
        return current

    @staticmethod
    def _batch_status(operations: list[Mapping[str, Any]]) -> str:
        statuses = [str(item.get("status") or "") for item in operations]
        if operations and all(status == "completed" for status in statuses):
            return "completed"
        if operations and all(status == "cancelled" for status in statuses):
            return "cancelled"
        if any(status in {"failed", "failed_integrity", "cancelled"} for status in statuses):
            return "failed"
        if any(status in {"waiting_tools", "waiting_host"} for status in statuses):
            return "waiting_host"
        if any(status == "waiting_goal_input" for status in statuses):
            return "waiting_goal_input"
        if any(status == "paused_budget" for status in statuses):
            return "paused_budget"
        return "running"

    def _run_batch(
        self,
        *,
        batch_session_id: str,
        summaries: list[Mapping[str, Any]] | None,
        observations: list[Mapping[str, Any]],
        cycle_actions: int,
        max_cycles: int,
        auto_continue: bool,
    ) -> dict[str, Any]:
        states = self.runtime.store.operations_for_batch(batch_session_id)
        known_run_ids = {state.run_id for state in states}
        if not known_run_ids and summaries:
            known_run_ids = {str(item.get("run_id") or "") for item in summaries if item.get("run_id")}
        if not known_run_ids:
            raise KeyError(f"batch_not_found:{batch_session_id}")
        observation_by_run: dict[str, Mapping[str, Any]] = {}
        for observation in observations:
            run_id = str(observation.get("run_id") or "").strip()
            if run_id not in known_run_ids:
                raise ValueError(f"batch_observation_run_mismatch:{run_id}")
            if run_id in observation_by_run:
                raise ValueError(f"duplicate_batch_observation:{run_id}")
            observation_by_run[run_id] = observation

        initial = {str(item.get("run_id") or ""): item for item in summaries or ()}
        results: list[dict[str, Any]] = []
        ordered_run_ids = [state.run_id for state in states] or sorted(known_run_ids)
        for run_id in ordered_run_ids:
            observation = observation_by_run.get(run_id)
            if observation is not None:
                action_id = str(observation.get("action_id") or "").strip()
                if not action_id:
                    current = self.runtime.status(run_id)
                    action_id = current.next_action or current.state.current_action_id
                if not action_id:
                    raise ValueError(f"observation_action_id_required:{run_id}")
                summary = self.runtime.submit_observation(
                    run_id=run_id,
                    action_id=action_id,
                    output=observation.get("output"),
                    tool=str(observation.get("tool") or "host-agent"),
                    continue_run=True,
                    max_actions=cycle_actions,
                ).summary()
            elif run_id in initial:
                summary = dict(initial[run_id])
            else:
                summary = self.runtime.resume(run_id, max_actions=cycle_actions).summary()
            results.append(
                self._continue_summary(
                    summary,
                    cycle_actions=cycle_actions,
                    max_cycles=max_cycles,
                    auto_continue=auto_continue,
                )
            )
        success = bool(results) and all(
            item.get("status") == "completed" and item.get("terminal", {}).get("success") is True
            for item in results
        )
        parent_session_id = (
            str(states[0].goal.starting_context.get("parent_session_id") or "")
            if states
            else ""
        )
        return {
            "batch_session_id": batch_session_id,
            "session_id": parent_session_id,
            "status": self._batch_status(results),
            "run_ids": [str(item.get("run_id") or "") for item in results],
            "operations": results,
            "pending_operations": [
                {
                    "run_id": item.get("run_id"),
                    "next_action": item.get("next_action"),
                    "next_action_spec": item.get("next_action_spec"),
                    "missing_capabilities": item.get("missing_capabilities", []),
                }
                for item in results
                if item.get("status") != "completed"
            ],
            "terminal": {
                "terminal": all(item.get("terminal", {}).get("terminal") is True for item in results),
                "success": success,
                "reason": "batch_goal_contract_satisfied" if success else "batch_goal_predicates_pending",
            },
            "automation_cycles": sum(int(item.get("automation_cycles") or 0) for item in results),
        }

    def handle(self, payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        method = str(payload.get("method") or "")
        request_id = payload.get("id")
        if not method:
            return self._error(request_id, -32600, "invalid_request")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                result: Any = {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "codex-redteam-runtime", "version": "1"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOL_DEFINITIONS}
            elif method == "tools/call":
                params = payload.get("params") if isinstance(payload.get("params"), Mapping) else {}
                tool_name = str(params.get("name") or "")
                definition = TOOL_DEFINITIONS_BY_NAME.get(tool_name)
                if definition is None:
                    raise ValueError(f"tool_not_found:{tool_name}")
                raw_arguments = params.get("arguments")
                arguments = raw_arguments if isinstance(raw_arguments, Mapping) else {}
                schema_error = ToolBroker._schema_error(definition["inputSchema"], arguments)
                if schema_error:
                    raise ValueError(schema_error)
                result = self._call_tool(tool_name, arguments)
            else:
                return self._error(request_id, -32601, f"method_not_found:{method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except KeyError as exc:
            return self._error(request_id, -32004, str(exc))
        except ValueError as exc:
            return self._error(request_id, -32602, str(exc))
        except Exception as exc:
            return self._error(request_id, -32000, f"runtime_error:{exc}")

    def _call_tool(self, name: str, raw_arguments: Any) -> Mapping[str, Any]:
        arguments = raw_arguments if isinstance(raw_arguments, Mapping) else {}
        if name == "redteam_run":
            run_id = str(arguments.get("run_id") or "").strip()
            batch_session_id = str(arguments.get("batch_session_id") or "").strip()
            observation = arguments.get("observation") if isinstance(arguments.get("observation"), Mapping) else None
            raw_observations = arguments.get("observations")
            observations = [item for item in raw_observations if isinstance(item, Mapping)] if isinstance(raw_observations, list) else []
            auto_continue = bool(arguments.get("auto_continue", True))
            cycle_actions = int(arguments.get("max_actions") or self.default_max_actions)
            max_cycles = max(1, min(64, int(arguments.get("max_cycles") or 16)))
            if run_id and batch_session_id:
                raise ValueError("run_id_and_batch_session_id_are_mutually_exclusive")
            if observation is not None and observations:
                raise ValueError("observation_and_observations_are_mutually_exclusive")
            if batch_session_id and observation is not None:
                raise ValueError("batch_requires_observations_array")
            if run_id and observations:
                raise ValueError("single_run_requires_observation_object")
            if batch_session_id:
                summary = self._run_batch(
                    batch_session_id=batch_session_id,
                    summaries=None,
                    observations=observations,
                    cycle_actions=cycle_actions,
                    max_cycles=max_cycles,
                    auto_continue=auto_continue,
                )
            elif not run_id:
                started = self._call_tool("redteam_start", arguments)
                summary = started["structuredContent"]
                if isinstance(summary.get("operations"), list):
                    summary = self._run_batch(
                        batch_session_id=str(summary.get("batch_session_id") or ""),
                        summaries=[item for item in summary["operations"] if isinstance(item, Mapping)],
                        observations=observations,
                        cycle_actions=cycle_actions,
                        max_cycles=max_cycles,
                        auto_continue=auto_continue,
                    )
                    summary["session_state_synced"] = sync_session_summary(
                        str(summary.get("session_id") or summary.get("batch_session_id") or ""), summary
                    )
                    return {
                        "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False, default=str)}],
                        "structuredContent": summary,
                        "isError": False,
                    }
                run_id = str(summary.get("run_id") or "")
                if not run_id or not auto_continue:
                    if isinstance(summary, dict):
                        summary["session_state_synced"] = sync_session_summary(
                            str(arguments.get("session_id") or ""), summary
                        )
                    return started
            elif observation is not None:
                action_id = str(observation.get("action_id") or "").strip()
                if not action_id:
                    current = self.runtime.status(run_id)
                    action_id = current.next_action or current.state.current_action_id
                if not action_id:
                    raise ValueError("observation_action_id_required")
                summary = self.runtime.submit_observation(
                    run_id=run_id,
                    action_id=action_id,
                    output=observation.get("output"),
                    tool=str(observation.get("tool") or "host-agent"),
                    continue_run=True,
                    max_actions=cycle_actions,
                ).summary()
            else:
                summary = self.runtime.resume(
                    run_id,
                    max_actions=cycle_actions,
                ).summary()
            if run_id:
                summary = self._continue_summary(
                    summary,
                    cycle_actions=cycle_actions,
                    max_cycles=max_cycles,
                    auto_continue=auto_continue,
                )
        elif name == "redteam_start":
            session_id = str(arguments.get("session_id") or "").strip()
            objective = str(arguments.get("objective") or "").strip()
            if not session_id or not objective:
                raise ValueError("session_id_and_objective_required")
            targets = arguments.get("targets")
            starting_context = arguments.get("starting_context") if isinstance(arguments.get("starting_context"), Mapping) else {}
            resolved_targets = (
                tuple(str(item) for item in targets if str(item).strip())
                if isinstance(targets, list)
                else self.runtime.compiler.extract_targets(objective)
                or self.runtime.compiler.extract_context_targets(starting_context)
            )
            if not resolved_targets:
                summary = {
                    "status": "waiting_goal_input",
                    "missing": ["target"],
                    "next_action": "retry redteam_start with targets or starting_context.target",
                }
            else:
                predicates = arguments.get("success_predicates")
                cycle_actions = int(arguments.get("max_actions") or self.default_max_actions)
                total_actions = int(arguments.get("max_total_actions") or max(256, cycle_actions))
                states = self.runtime.start_batch(
                    session_id=session_id,
                    objective=objective,
                    targets=resolved_targets,
                    workflow_hint=str(arguments.get("workflow_hint") or ""),
                    starting_context=starting_context,
                    constraints=arguments.get("constraints") if isinstance(arguments.get("constraints"), Mapping) else {},
                    success_predicates=predicates if isinstance(predicates, list) else (),
                    max_actions=total_actions,
                    max_retries_per_action=int(
                        arguments.get("max_retries_per_action", self.default_max_retries_per_action)
                    ),
                )
                results = [self.runtime.resume(state.run_id, max_actions=cycle_actions).summary() for state in states]
                if len(results) == 1:
                    summary = results[0]
                else:
                    batch_session_id = str(states[0].goal.starting_context.get("batch_session_id") or "")
                    summary = self._run_batch(
                        batch_session_id=batch_session_id,
                        summaries=results,
                        observations=[],
                        cycle_actions=cycle_actions,
                        max_cycles=1,
                        auto_continue=False,
                    )
        elif name == "redteam_resume":
            summary = self.runtime.resume(
                str(arguments.get("run_id") or ""),
                max_actions=int(arguments.get("max_actions") or self.default_max_actions),
            ).summary()
        elif name == "redteam_status":
            summary = self.runtime.status(str(arguments.get("run_id") or "")).summary()
        elif name == "redteam_submit_observation":
            summary = self.runtime.submit_observation(
                run_id=str(arguments.get("run_id") or ""),
                action_id=str(arguments.get("action_id") or ""),
                output=arguments.get("output"),
                tool=str(arguments.get("tool") or "host-agent"),
                continue_run=bool(arguments.get("continue_run", True)),
                max_actions=self.default_max_actions,
            ).summary()
        elif name == "redteam_evidence":
            run_id = str(arguments.get("run_id") or "")
            evidence_id = str(arguments.get("evidence_id") or "")
            node = next(
                (item for item in self.runtime.evidence_graph.list(run_id) if item.evidence_id == evidence_id),
                None,
            )
            if node is None:
                raise KeyError(f"evidence_not_found:{evidence_id}")
            summary = node.to_dict()
        elif name == "redteam_cancel":
            run_id = str(arguments.get("run_id") or "").strip()
            batch_session_id = str(arguments.get("batch_session_id") or "").strip()
            if bool(run_id) == bool(batch_session_id):
                raise ValueError("exactly_one_of_run_id_or_batch_session_id_required")
            reason = str(arguments.get("reason") or "user_requested")
            if run_id:
                summary = self.runtime.cancel(run_id, reason=reason).summary()
            else:
                states = self.runtime.store.operations_for_batch(batch_session_id)
                if not states:
                    raise KeyError(f"batch_not_found:{batch_session_id}")
                results = []
                for state in states:
                    if state.status in {"completed", "failed", "failed_integrity"}:
                        results.append(self.runtime.status(state.run_id).summary())
                    else:
                        results.append(self.runtime.cancel(state.run_id, reason=reason).summary())
                summary = self._run_batch(
                    batch_session_id=batch_session_id,
                    summaries=results,
                    observations=[],
                    cycle_actions=self.default_max_actions,
                    max_cycles=1,
                    auto_continue=False,
                )
                if all(item.get("status") == "cancelled" for item in summary["operations"]):
                    summary["status"] = "cancelled"
                    summary["terminal"] = {
                        "terminal": True,
                        "success": False,
                        "reason": "batch_cancelled",
                    }
        elif name == "redteam_events":
            run_id = str(arguments.get("run_id") or "")
            events = self.runtime.store.events(
                run_id,
                after_event_id=int(arguments.get("after_event_id") or 0),
                limit=int(arguments.get("limit") or 200),
            )
            summary = {
                "run_id": run_id,
                "events": list(events),
                "next_event_id": events[-1]["event_id"] if events else None,
            }
        else:
            raise ValueError(f"tool_not_found:{name}")
        if name in {
            "redteam_run",
            "redteam_start",
            "redteam_resume",
            "redteam_status",
            "redteam_submit_observation",
            "redteam_cancel",
        } and isinstance(summary, Mapping):
            if summary.get("batch_session_id"):
                bridge_session_id = str(summary.get("session_id") or summary.get("batch_session_id") or "")
            else:
                bridge_run_id = str(summary.get("run_id") or arguments.get("run_id") or "")
                bridge_state = self.runtime.store.load_operation(bridge_run_id) if bridge_run_id else None
                bridge_session_id = bridge_state.session_id if bridge_state is not None else str(arguments.get("session_id") or "")
            if isinstance(summary, dict):
                summary["session_state_synced"] = sync_session_summary(bridge_session_id, summary)
        return {
            "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False, default=str)}],
            "structuredContent": summary,
            "isError": False,
        }

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> Mapping[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _default_config_paths(explicit: list[str]) -> list[Path]:
    paths = [Path(item).expanduser().resolve(strict=False) for item in explicit]
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser().resolve(strict=False)
    default = codex_home / "config.toml"
    if default not in paths:
        paths.append(default)
    return paths


def _runtime_settings(paths: list[Path]) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "max_actions_per_cycle": 64,
        "action_timeout_seconds": None,
        "max_retries_per_action": 2,
        "max_hypothesis_branches": 4,
    }
    for path in paths:
        if not path.is_file():
            continue
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        automation = payload.get("automation") if isinstance(payload.get("automation"), Mapping) else {}
        if automation.get("max_actions_per_cycle") is not None:
            settings["max_actions_per_cycle"] = max(1, min(512, int(automation["max_actions_per_cycle"])))
        if automation.get("action_timeout_seconds") is not None:
            settings["action_timeout_seconds"] = max(0.1, float(automation["action_timeout_seconds"]))
        if automation.get("max_retries_per_action") is not None:
            settings["max_retries_per_action"] = max(0, min(8, int(automation["max_retries_per_action"])))
        if automation.get("max_hypothesis_branches") is not None:
            settings["max_hypothesis_branches"] = max(1, min(8, int(automation["max_hypothesis_branches"])))
        break
    return settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Codex red-team durable MCP runtime")
    parser.add_argument("--root", default="", help="Durable state root")
    parser.add_argument("--config", action="append", default=[], help="Codex config.toml path")
    arguments = parser.parse_args(argv)
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser().resolve(strict=False)
    root = Path(arguments.root).expanduser().resolve(strict=False) if arguments.root else codex_home / "redteam-mode" / "operations"
    config_paths = _default_config_paths(arguments.config)
    settings = _runtime_settings(config_paths)
    broker = ToolBroker()
    broker.discover_from_configs(config_paths)
    runtime = OperationRuntime(
        root=root,
        broker=broker,
        action_timeout_cap=settings["action_timeout_seconds"],
        planner=AdaptivePlanner(
            max_hypothesis_branches=settings["max_hypothesis_branches"],
        ),
    )
    server = RuntimeMcpServer(
        runtime,
        default_max_actions=settings["max_actions_per_cycle"],
        default_max_retries_per_action=settings["max_retries_per_action"],
    )
    try:
        for line in sys.stdin:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse_error"}}
            else:
                response = server.handle(payload) if isinstance(payload, Mapping) else server._error(None, -32600, "invalid_request")
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
    finally:
        broker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
