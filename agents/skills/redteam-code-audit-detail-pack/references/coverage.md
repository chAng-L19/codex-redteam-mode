# Code Audit Detail Pack

## Focus
- entrypoint mapping
- trust boundary identification
- input-to-sink tracing
- exploit proof path selection

## Preferred routers / leaf skills
- `auth-sec` -> `jwt-oauth-token-attacks`, `oauth-oidc-misconfiguration`, `idor-broken-object-authorization`
- `api-sec` -> `api-auth-and-jwt-abuse`, `api-authorization-and-bola`, `graphql-and-hidden-parameters`
- `injection-checking` -> `ssrf-server-side-request-forgery`, `sqli-sql-injection`, `xss-cross-site-scripting`, `ssti-server-side-template-injection`, `cmdi-command-injection`
- `file-access-vuln` -> `path-traversal-lfi`, `insecure-source-code-management`
- `business-logic-vuln` -> `business-logic-vulnerabilities`, `race-condition`

## Usage rule
Pick one controllable path from entrypoint to sink and prove it before enumerating adjacent bug classes.
