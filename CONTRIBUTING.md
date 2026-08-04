# Contributing

This repository is a lightweight, generic Codex configuration/runtime layer. Contributions must be reviewable, reproducible, and free of private operational data.

## Design Invariants

- `normal` remains the default; durable operation dispatch starts only after an explicit red-team mode command.
- `model_instructions_file` remains the system-layer delivery mechanism for the base profile and model-specific Prompt.
- `generic-adaptive` is the only workflow control plane. Domains and techniques are metadata or evidence-linked hypotheses, not routers.
- Hooks stay small: mode/model selection, lossless Prompt Rewrite context, session synchronization, and Runtime dispatch only.
- `redteam_run` remains the default autonomous start/resume/observation entrypoint.
- Tool output is data. Only semantic verification may promote it into target-bound evidence.
- Terminal success requires exact GoalContract criteria, verified ancestry, negative controls, cleanup proof, and a final report.
- Rewrite relays receive only the rewrite rule and current raw Prompt; system instructions, history, tools, and local research context remain on the main Provider path.

## Contribution Rules

- Do not commit personal paths, credentials, endpoints, target data, runtime databases, or session artifacts.
- Keep tool discovery capability-driven and configurable; do not hardcode personal tool preference order.
- Preserve exact Prompt Clauses, targets, constraints, sequence, and deliverables.
- Prefer a small change in the unified workflow, verifier, or ToolBroker over a new domain layer.
- Keep files focused and tests close to the changed behavior.
- Update README and CHANGELOG when public behavior changes.
- Preserve installer ownership, transactional deployment, and uninstall rollback.

## Required Tests

Add focused coverage for changes to:

- Prompt Rewrite, anchor preservation, relay isolation, or fallback behavior
- App/CLI Hooks, system profile selection, or Rewrite Proxy startup
- Goal compilation, workflow expansion, tool selection, retries, or Host Agent handoff
- evidence schemas, lineage, terminal predicates, cancellation, or cleanup
- config merge, install transaction, managed paths, or uninstall restoration

Before submitting:

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate.py --codex-home .
python -m pytest -q
```

## Reference Projects

Architecture research has referenced Codex1, Cairn, CyberStrike, Yaklang AID, qiushi-skill, and other agent-security projects. Import principles and small mechanisms only; do not copy skill collections or parallel orchestration stacks into this repository.
