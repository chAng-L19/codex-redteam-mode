from __future__ import annotations
import re
from .mappings import PHASE_DEFAULT_ROUTER

FILE_PATTERNS = r"\b(upload|download|file|filepath|lfi|traversal|source exposure|write)\b|上传|下载|文件|文件路径|路径遍历|本地文件|任意写入"
AUTH_PATTERNS = r"\b(jwt|oauth|oidc|saml|session|login|auth|token|bola|idor)\b|登录|鉴权|会话|令牌|越权"
API_PATTERNS = r"\b(api|graphql|swagger|openapi|json)\b|接口|文档|schema|graphql"
INJECTION_PATTERNS = r"\b(ssrf|sqli|sql injection|xss|ssti|cmdi|xxe|deserialization|jndi|xslt|expression language|crlf)\b|注入|反序列化|模板|命令执行"
LOGIC_PATTERNS = r"\b(race|logic|workflow|state machine|business)\b|业务逻辑|竞态|流程缺陷"

def select_router(prompt: str, phase: str) -> str:
    p = prompt
    if phase == "web":
        if re.search(AUTH_PATTERNS, p, re.I): return "auth-sec"
        if re.search(API_PATTERNS, p, re.I): return "api-sec"
        if re.search(FILE_PATTERNS, p, re.I): return "file-access-vuln"
        if re.search(LOGIC_PATTERNS, p, re.I): return "business-logic-vuln"
        if re.search(INJECTION_PATTERNS, p, re.I): return "injection-checking"
        return "recon-for-sec"
    if phase == "ad":
        if re.search(r"\b(adcs|cert|certificate)\b|证书服务|证书模板", p, re.I): return "active-directory-certificate-services"
        if re.search(r"\b(acl|genericall|writeowner|writedacl)\b|ACL|委派权限|writeowner|writedacl", p, re.I): return "active-directory-acl-abuse"
        if re.search(r"\b(ntlm|relay|responder)\b|NTLM|中继|强制认证", p, re.I): return "ntlm-relay-coercion"
        return "active-directory-kerberos-attacks"
    if phase == "postex": return "post-exploitation-playbook"
    if phase == "reverse": return "malware-loader-analysis"
    if phase == "code-audit":
        if re.search(AUTH_PATTERNS, p, re.I): return "auth-sec"
        if re.search(API_PATTERNS, p, re.I): return "api-sec"
        if re.search(FILE_PATTERNS, p, re.I): return "file-access-vuln"
        if re.search(LOGIC_PATTERNS, p, re.I): return "business-logic-vuln"
        if re.search(INJECTION_PATTERNS, p, re.I): return "injection-checking"
        return "hack"
    if phase == "payload": return "weaponization-and-payloads"
    if phase == "evasion": return "windows-av-evasion"
    if phase == "cloud": return "cloud-iam-abuse"
    if phase == "container":
        if re.search(r"\b(hostpath|privileged|escape|breakout|cap_sys_admin)\b|hostPath|特权容器|逃逸", p, re.I): return "container-escape-techniques"
        return "kubernetes-pentesting"
    if phase == "network":
        if re.search(r"\bwebsocket|ws\b|WebSocket", p, re.I): return "websocket-security"
        if re.search(r"http/2|h2\b|HTTP/2", p, re.I): return "http2-specific-attacks"
        if re.search(r"\b(smuggling|desync)\b|请求走私", p, re.I): return "request-smuggling"
        if re.search(r"\bdns rebinding\b|DNS重绑定", p, re.I): return "dns-rebinding-attacks"
        return "network-protocol-attacks"
    if phase == "crypto":
        if re.search(r"\b(md5|sha1|sha256|hash|length extension)\b|哈希|长度扩展", p, re.I): return "hash-attack-techniques"
        if re.search(r"\b(aes|des|cbc|gcm|ctr|padding oracle)\b|对称加密|填充预言机", p, re.I): return "symmetric-cipher-attacks"
        if re.search(r"\b(lattice|lwe|ntru)\b|格密码", p, re.I): return "lattice-crypto-attacks"
        if re.search(r"\b(stego|steganography)\b|隐写", p, re.I): return "steganography-techniques"
        if re.search(r"\b(caesar|vigenere|classical cipher)\b|古典密码", p, re.I): return "classical-cipher-analysis"
        return "rsa-attack-techniques"
    if phase == "mobile":
        if re.search(r"\b(ssl pinning|certificate pinning|frida|objection)\b|证书锁定|SSL Pinning", p, re.I): return "mobile-ssl-pinning-bypass"
        if re.search(r"\b(ios|ipa|swift|xcode)\b|iOS|苹果", p, re.I): return "ios-pentesting-tricks"
        return "android-pentesting-tricks"
    return PHASE_DEFAULT_ROUTER.get(phase, "hack")
