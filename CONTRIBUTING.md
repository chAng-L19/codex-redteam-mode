# Contributing

This repository should remain a **generic GitHub edition**, not a copy of any personal local environment. All contributions must be reviewable, reproducible, and free of private operational data.

## Purpose

The goal of this project is to provide a lightweight, opt-in red-team runtime/configuration layer for Codex. Contributions should strengthen routing, improve adapter-based automation, or expand pack coverage — without bloating the context window or compromising normal-mode behavior.

## Contribution Rules

- **No personal local paths** — do not commit absolute paths, user directories, or environment-specific configs
- **No personal browser/tool preferences** — keep tool references generic and configurable
- **No private target data** — no IP addresses, hostnames, credentials, or operational details
- **Documentation must reflect actual runtime behavior** — if code changes, update the docs in the same PR
- **Keep hooks lightweight and testable** — compact hooks are easier to audit and less likely to introduce side effects
- **Prefer pack-first routing** — when updating skill coverage, add or refine a detail pack rather than modifying the doctrine envelope
- **Preserve opt-in behavior** — normal mode must not be affected by red-team changes
- **Write tests for new routing paths** — any new phase/pack combination should have corresponding validation
- **Write tests for automation adapters and gates** — any executor adapter, retry path, scope rule, artifact gate, or report gate change should have focused coverage

## Avoid

- Personal configs, local tool paths, or environment-specific settings
- Private prompts or overlays not intentionally generalized for public use
- Documentation that does not match current code behavior
- Heavy prompt additions that increase context cost without improving routing quality
- Breaking changes to the `phase -> router -> pack -> leaf` mainline without discussion
- Adapter code that bypasses Tool Registry, Scope Gate, Executor, artifact recording, or report gates
- Committing generated runtime state files or session artifacts

## Security Notice

This repository is intended for **authorized penetration testing, red-team research, and defensive security experimentation**. The GitHub version must remain:

- **Generic** — no hardcoded targets, paths, or operational data
- **Reproducible** — anyone should be able to install and validate with the same results
- **Reviewable** — every change should be auditable for safety and correctness
- **Free of private operational data** — sanitize all examples and test fixtures

Before submitting a PR, verify:

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m pytest -q
```

## Acknowledgements

### Individual Contributors

- **Mingxi / 洺熙** — suggested adding semantic judgment as fallback for phase detection (2026-05-07); proposed removing the methodology layer and subdividing skills for smarter AI behavior during work phases (2026-05-14)
- **Nirvana** — proposed workflow optimization with overlay installation enablement (2026-05-11)
- **PINGS** — offered jailbreak text enhancements and robustness improvements (2026-05-16)

### Reference Projects

Method layer, routing layer, and skill pack structure draw inspiration from:

- [qiushi-skill](https://github.com/qiushi-L/qiushi-skill)
- [yaklang/hack-skills](https://github.com/yaklang/hack-skills)
- [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)

Thank you to all contributors and reference projects that helped shape this repository.
