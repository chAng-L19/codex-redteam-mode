# Design Notes

## Why this profile is opt-in

Always-on red-team profiles tend to create three problems:

1. ordinary work is reinterpreted as offensive work
2. session-start context becomes too heavy
3. long doctrine blocks pollute context and make recovery worse

This project deliberately avoids that by using:

- explicit mode toggles
- lightweight hook output
- a compact doctrine skill with external references

## Why state lives in temp

The runtime mode state is stored in a temp file so that:

- hooks can coordinate mode between prompts
- the state resets naturally with new sessions
- the repository itself remains static and publishable

## Why the doctrine is split into references

The live prompt path should stay short. Large phase guidance belongs in reference files that are opened only when needed.
