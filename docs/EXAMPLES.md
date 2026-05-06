# Examples

## Example 1 — normal work stays normal

User:

```text
帮我写一个 React 页面
```

Result:

- no offensive injection
- handled as ordinary implementation work

## Example 2 — explicit red-team activation

User:

```text
进入红队模式
```

Then:

```text
请帮我分析 Burp 里的 SSRF 利用链并给出下一步
```

Result:

- red-team mode enabled
- phase routed to `web`
- compact offensive guidance injected

## Example 3 — return to normal

User:

```text
退出红队模式
```

Result:

- offensive injection stops immediately
- later prompts are handled in normal mode again
