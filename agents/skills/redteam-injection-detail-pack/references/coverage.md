        # redteam-injection-detail-pack

        ## Focus
        - server-side fetch abuse
- database query control
- template / expression execution
- XML / serialization / command sinks

        ## Preferred leaf skills
        - `ssrf-server-side-request-forgery`
- `sqli-sql-injection`
- `xss-cross-site-scripting`
- `ssti-server-side-template-injection`
- `cmdi-command-injection`
- `xxe-xml-external-entity`
- `deserialization-insecure`
- `jndi-injection`
- `xslt-injection`
- `expression-language-injection`
- `crlf-injection`

        ## Usage rule
        Open only the leaf skill that matches the current request path. Keep the pack as a compact router and checklist, not a heavy prompt blob.
