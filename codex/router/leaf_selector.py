from __future__ import annotations
import re

def select_subphase(prompt: str, phase: str) -> str:
    if phase == "reverse":
        if re.search(r"\b(loader|stager|dropper|callback|payload)\b|loader|样本|阶段|回调|释放资源", prompt, re.I): return "loader"
        if re.search(r"\b(heap|rop|overflow|format string|primitive)\b|heap|rop|溢出|原语", prompt, re.I): return "exploitability"
        return "binary"
    if phase == "code-audit":
        if re.search(r"\b(entry|entrypoint|controller|handler|middleware)\b|入口|控制器|处理器|中间件", prompt, re.I): return "entrypoint"
        if re.search(r"\b(sink|dangerous function|query|exec|template)\b|sink|危险函数|危险调用", prompt, re.I): return "leaf"
        return "route"
    if phase == "evasion":
        if re.search(r"\b(waf|cdn|header|smuggling|403|csp)\b|WAF|403|CSP|请求走私", prompt, re.I): return "network"
        if re.search(r"\b(av|edr|defender|sandbox)\b|免杀|杀软|沙箱|EDR", prompt, re.I): return "host"
    return ""

def select_leaf_skill(prompt: str, phase: str, router: str) -> str:
    p = prompt
    if router == "auth-sec":
        if re.search(r"\b(jwt|token)\b|令牌|JWT", p, re.I): return "jwt-oauth-token-attacks"
        if re.search(r"\b(oauth|oidc)\b|OAuth|OIDC", p, re.I): return "oauth-oidc-misconfiguration"
        if re.search(r"\b(saml)\b|SAML", p, re.I): return "saml-sso-assertion-attacks"
        if re.search(r"\b(idor|bola)\b|越权|BOLA|IDOR", p, re.I): return "idor-broken-object-authorization"
        return "authbypass-authentication-flaws"
    if router == "api-sec":
        if re.search(r"\b(graphql)\b|GraphQL", p, re.I): return "graphql-and-hidden-parameters"
        if re.search(r"\b(jwt|token|auth)\b|鉴权|令牌", p, re.I): return "api-auth-and-jwt-abuse"
        if re.search(r"\b(hpp|parameter pollution)\b|参数污染", p, re.I): return "http-parameter-pollution"
        return "api-authorization-and-bola"
    if router == "injection-checking":
        if re.search(r"\bssrf\b|SSRF", p, re.I): return "ssrf-server-side-request-forgery"
        if re.search(r"\bsqli?\b|SQL注入", p, re.I): return "sqli-sql-injection"
        if re.search(r"\bxss\b|XSS", p, re.I): return "xss-cross-site-scripting"
        if re.search(r"\bssti\b|SSTI", p, re.I): return "ssti-server-side-template-injection"
        if re.search(r"\b(cmdi|command injection)\b|命令注入", p, re.I): return "cmdi-command-injection"
        if re.search(r"\bxxe\b|XXE|XML外部实体", p, re.I): return "xxe-xml-external-entity"
        if re.search(r"\bjndi\b|JNDI", p, re.I): return "jndi-injection"
        if re.search(r"\bxslt\b|XSLT", p, re.I): return "xslt-injection"
        if re.search(r"\bexpression language\b|EL注入", p, re.I): return "expression-language-injection"
        if re.search(r"\bcrlf\b|CRLF", p, re.I): return "crlf-injection"
        return "deserialization-insecure"
    if router == "file-access-vuln":
        if re.search(r"\blfi\b|\btraversal\b|LFI|路径遍历", p, re.I): return "path-traversal-lfi"
        if re.search(r"\b(upload|write)\b|上传|任意写入", p, re.I): return "arbitrary-write-to-rce"
        return "insecure-source-code-management"
    if router == "business-logic-vuln":
        if re.search(r"\brace\b|竞态", p, re.I): return "race-condition"
        if re.search(r"\bprototype pollution\b|原型污染", p, re.I): return "prototype-pollution"
        if re.search(r"\btype juggling\b|弱比较", p, re.I): return "type-juggling"
        return "business-logic-vulnerabilities"
    if router in {"active-directory-kerberos-attacks","active-directory-acl-abuse","active-directory-certificate-services","ntlm-relay-coercion","malware-loader-analysis","cloud-iam-abuse","kubernetes-pentesting","container-escape-techniques","network-protocol-attacks","websocket-security","http2-specific-attacks","request-smuggling","dns-rebinding-attacks","rsa-attack-techniques","hash-attack-techniques","symmetric-cipher-attacks","lattice-crypto-attacks","steganography-techniques","classical-cipher-analysis","android-pentesting-tricks","ios-pentesting-tricks","mobile-ssl-pinning-bypass"}: return router
    if router == "post-exploitation-playbook":
        if re.search(r"\b(credential|token|cookie|ssh key|kubeconfig)\b|凭证|cookie|令牌|ssh key", p, re.I): return "credential-access-operations"
        if re.search(r"\blinux\b|Linux", p, re.I): return "linux-privilege-escalation"
        if re.search(r"\b(pivot|tunnel|socks|chisel)\b|隧道|代理", p, re.I): return "tunneling-and-pivoting"
        return "windows-privilege-escalation"
    if router == "windows-av-evasion":
        if re.search(r"\bwaf\b|WAF|403", p, re.I): return "waf-bypass-techniques"
        if re.search(r"\bcsp\b|CSP", p, re.I): return "csp-bypass-advanced"
        if re.search(r"\bsandbox\b|沙箱", p, re.I): return "sandbox-escape-techniques"
        if re.search(r"\b(defender|av|edr)\b|杀软|免杀|EDR", p, re.I): return "windows-av-evasion"
        return "401-403-bypass-techniques"
    if router == "weaponization-and-payloads":
        if re.search(r"\b(persistence|beacon|c2)\b|持久化|回连|信标", p, re.I): return "persistence-and-c2"
        if re.search(r"\b(delivery|phish|initial access)\b|投递|入口", p, re.I): return "initial-access-delivery"
        return "weaponization-and-payloads"
    if phase == "web": return "recon-for-sec"
    return "hack"
