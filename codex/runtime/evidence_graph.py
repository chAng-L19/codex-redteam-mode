from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .durable_store import DurableStore
from .models import EvidenceNode
from .security import redact_sensitive, secure_directory, secure_file


class EvidenceGraph:
    def __init__(self, store: DurableStore, artifact_root: Path) -> None:
        self.store = store
        self.artifact_root = artifact_root
        secure_directory(self.artifact_root)

    @staticmethod
    def content_hash(payload: Any) -> str:
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def add(
        self,
        *,
        run_id: str,
        action_id: str,
        artifact_type: str,
        target: str,
        tool: str,
        payload: Any,
        parent_ids: Sequence[str],
        verifier: str,
        confidence: float,
    ) -> EvidenceNode:
        stored_nodes = self.store.evidence(run_id)
        existing = {node.evidence_id: node for node in stored_nodes}
        missing_parents = set(parent_ids) - set(existing)
        if missing_parents:
            raise ValueError(f"evidence_parent_missing:{sorted(missing_parents)}")
        payload = redact_sensitive(payload)
        digest = self.content_hash(payload)
        for stored in stored_nodes:
            if (
                stored.action_id == action_id
                and stored.artifact_type == artifact_type
                and stored.tool == tool
                and stored.content_hash == digest
            ):
                self._write_artifact(stored)
                return stored
        identity = hashlib.sha256(f"{run_id}\0{action_id}\0{artifact_type}\0{tool}\0{digest}".encode("utf-8")).hexdigest()
        node = EvidenceNode(
            evidence_id=f"evidence-{identity[:32]}",
            run_id=run_id,
            action_id=action_id,
            artifact_type=artifact_type,
            target=target,
            tool=tool,
            payload=payload,
            content_hash=digest,
            parent_ids=tuple(parent_ids),
            verifier=verifier,
            confidence=max(0.0, min(1.0, float(confidence))),
            verified=True,
        )
        self._write_artifact(node)
        self.store.save_evidence(node)
        persisted = self.find_by_content(run_id, action_id, artifact_type, digest, tool=tool)
        return persisted or node

    def _write_artifact(self, node: EvidenceNode) -> Path:
        path = self._artifact_path(node)
        secure_directory(path.parent)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(node.to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        secure_file(temporary)
        temporary.replace(path)
        secure_file(path)
        return path

    def _artifact_path(self, node: EvidenceNode) -> Path:
        safe_run = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.run_id)
        safe_action = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.action_id)
        safe_type = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.artifact_type)
        tool_digest = hashlib.sha256(node.tool.encode("utf-8", errors="replace")).hexdigest()[:8]
        return self.artifact_root / safe_run / f"{safe_action}-{safe_type}-{node.content_hash[:12]}-{tool_digest}.json"

    def list(self, run_id: str) -> tuple[EvidenceNode, ...]:
        nodes = self.store.evidence(run_id)
        valid: list[EvidenceNode] = []
        for node in nodes:
            if not node.verified or node.content_hash != self.content_hash(node.payload):
                continue
            path = self._artifact_path(node)
            source_path = path
            if not source_path.is_file():
                legacy_path = self._legacy_artifact_path(node)
                if legacy_path.is_file():
                    source_path = legacy_path
            try:
                persisted = json.loads(source_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(persisted, dict):
                continue
            persisted_node = EvidenceNode.from_dict(persisted)
            if persisted_node.to_dict() != node.to_dict():
                continue
            if source_path != path:
                self._write_artifact(node)
            valid.append(node)
        return tuple(valid)

    def find_by_content(
        self,
        run_id: str,
        action_id: str,
        artifact_type: str,
        digest: str,
        *,
        tool: str = "",
    ) -> EvidenceNode | None:
        for node in self.list(run_id):
            if (
                node.action_id == action_id
                and node.artifact_type == artifact_type
                and node.content_hash == digest
                and (not tool or node.tool == tool)
            ):
                return node
        return None

    def _legacy_artifact_path(self, node: EvidenceNode) -> Path:
        safe_run = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.run_id)
        safe_action = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.action_id)
        safe_type = "".join(character if character.isalnum() or character in "._-" else "_" for character in node.artifact_type)
        return self.artifact_root / safe_run / f"{safe_action}-{safe_type}-{node.content_hash[:12]}.json"

    def by_type(self, run_id: str, artifact_type: str) -> tuple[EvidenceNode, ...]:
        return tuple(node for node in self.list(run_id) if node.artifact_type == artifact_type)
