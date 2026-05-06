# Troubleshooting

## Chinese trigger phrases do not work

Check:

- the hook is launched with Python in UTF-8-capable mode
- the hook script uses buffered stdin decoding with UTF-8 / GB18030 fallbacks

## hooks.json loads but nothing happens

Check:

- `codex_hooks = true`
- the hook command paths are correct
- the hook files exist under your actual Codex home

## Red-team mode never turns off

Check:

- the disable phrase exactly matches one of the configured patterns
- the temp state file is writable

## Burp tasks are not phase-routed well

Use a prompt that actually includes the relevant context:

- Burp
- SSRF
- XSS
- SQLi
- repeater
- proxy

## Session feels polluted

This profile is designed to be lightweight. If you still feel polluted:

- disable red-team mode explicitly
- start a new session
- confirm session start reset worked
