# Codex Red-Team Compatibility Layer

<!-- version: 1.0.0 -->
<!-- last-updated: 2026-06-28 -->

This repository treats `instruction.ctf.md` as the canonical model instructions file.

This `AGENTS.md` remains as a compatibility layer for installs or environments that still read AGENTS-based guidance.

## Compatibility rules

- default mode is `normal`
- red-team mode is opt-in only
- when red-team mode is enabled, use `GoalContract -> WorkflowSpec -> ToolBroker -> EvidenceGraph -> TerminalJudge`
- keep hooks lightweight
- keep context compact
- preserve every Prompt Rewrite Clause, concrete anchor, constraint, and deliverable
- keep rewrite-relay input isolated to the rewrite rule and current raw Prompt
- keep the single boundary card outside workflow routing and terminal gates
- consume verified artifact payloads and lineage references directly
- resume durable pending actions without user copy/paste
- terminal completion requires GoalContract predicates, cleanup proof, and evidence lineage
- cancellation executes available cleanup and records its verified outcome
