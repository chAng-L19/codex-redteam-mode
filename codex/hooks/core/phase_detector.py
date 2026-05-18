from __future__ import annotations

import re
from typing import Optional

from .semantic_phase import classify_phase_semantically

SEMANTIC_THRESHOLD = 0.10

SECURITY_PATTERNS = [
    ("web", [r"\b(xss|sqli|sqli?|ssrf|ssti|idor|csrf|xxe|cmdi|graphql|api|swagger|openapi|burp|repeater|proxy)\b", r"SQL注入", r"SSRF", r"XXE", r"XSS", r"SSTI", r"越权", r"注入", r"请求", r"响应", r"接口", r"鉴权", r"登录"]),
    ("ad", [r"\b(kerberos|ntlm|adcs|bloodhound|acl|delegation|kerberoast|asreproast)\b", r"域控", r"委派", r"票据", r"证书服务", r"域内横向"]),
    ("postex", [r"\b(post[- ]?ex|foothold|shell|privilege escalation|lateral movement|pivot)\b", r"拿到 shell", r"提权", r"横向", r"落地后", r"主机分诊"]),
    ("reverse", [r"\b(reverse|reverse engineer(?:ing)?|malware|dropper|stager|loader|sample|unpack(?:ing)?|execution chain|decompile|binary)\b", r"逆向", r"反编译", r"样本", r"执行链", r"脱壳", r"二进制"]),
    ("code-audit", [r"\b(code audit|source code|controller|handler|middleware|grep|taint|sink|entrypoint)\b", r"源码", r"审计", r"入口", r"控制器", r"中间件", r"危险函数", r"信任边界"]),
    ("payload", [r"\b(payload|shellcode|staged|stageless|launcher|beacon)\b", r"载荷", r"启动器", r"shellcode", r"回连", r"信标"]),
    ("cloud", [r"\b(aws|azure|gcp|iam|sts|role assumption|cloudtrail|metadata service)\b", r"AWS", r"Azure", r"GCP", r"云", r"云凭证", r"元数据服务"]),
    ("container", [r"\b(kubernetes|k8s|helm|container|docker|pod|namespace|hostpath|privileged)\b", r"K8S", r"容器", r"集群", r"逃逸", r"Pod"]),
    ("network", [r"\b(http/2|websocket|ws|request smuggling|dns rebinding|protocol|tcp|udp|packet|pcap)\b", r"协议", r"流量", r"抓包", r"请求走私", r"WebSocket", r"DNS重绑定"]),
    ("crypto", [r"\b(rsa|aes|des|hash|sha|md5|padding oracle|lattice|cipher|stego)\b", r"密码学", r"加密", r"哈希", r"侧信道", r"隐写"]),
    ("mobile", [r"\b(android|ios|apk|ipa|frida|objection|pinning|mobile)\b", r"安卓", r"苹果", r"移动端", r"证书锁定", r"抓包"]),
    ("evasion", [r"\b(edr|av|defender|waf|403|csp|bypass|sandbox)\b", r"免杀", r"绕过", r"沙箱", r"对抗", r"WAF"]),
]


def detect_phase_rule_based(prompt: str) -> Optional[str]:
    for phase, patterns in SECURITY_PATTERNS:
        for pat in patterns:
            if re.search(pat, prompt, re.I):
                return phase
    return None


def detect_phase(prompt: str) -> str:
    matched = detect_phase_rule_based(prompt)
    if matched:
        return matched
    phase, score = classify_phase_semantically(prompt)
    if phase and score >= SEMANTIC_THRESHOLD:
        return phase
    return "general"
