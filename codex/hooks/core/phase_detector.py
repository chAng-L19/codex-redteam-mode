from __future__ import annotations

import re
from typing import Optional

from .semantic_phase import classify_phase_semantically


SEMANTIC_THRESHOLD = 0.25

SECURITY_PATTERNS = [
    (
        "warmup",
        [
            r"\b(osint|fingerprint|tech stack|technology stack|cms|framework version|built with)\b",
            "技术栈",
            "网站指纹",
            "组件识别",
            "指纹",
        ],
    ),
    (
        "defense",
        [
            r"\b(waf rule|csp policy|security header|authorization model|rbac|access control model|defense mechanism|rate limit|cors policy)\b",
            "防护机制",
            "安全策略",
            "授权模型",
            "访问控制",
        ],
    ),
    (
        "web",
        [
            r"\b(xss|sqli|sql injection|ssrf|ssti|idor|csrf|xxe|cmdi|graphql|api|swagger|openapi|burp|repeater|proxy|upload|download|lfi|traversal|race condition|business logic|bola|open redirect|jwt|oauth|oidc|saml|session|login|auth|token)\b",
            "SQL注入",
            "SSRF",
            "XXE",
            "XSS",
            "SSTI",
            "越权",
            "请求",
            "响应",
            "接口",
            "鉴权",
            "登录",
            "上传",
            "下载",
            "文件",
            "竞态",
            "业务逻辑",
        ],
    ),
    (
        "ad",
        [
            r"\b(kerberos|ntlm|adcs|bloodhound|acl|delegation|kerberoast|asreproast)\b",
            "域控",
            "委派",
            "票据",
            "证书服务",
            "域内横向",
        ],
    ),
    (
        "postex",
        [
            r"\b(post[- ]?ex|foothold|shell|privilege escalation|lateral movement|pivot)\b",
            "拿到 shell",
            "提权",
            "横向",
            "落地",
            "主机分析",
        ],
    ),
    (
        "reverse",
        [
            r"\b(reverse|reverse engineer(?:ing)?|malware|dropper|stager|loader|sample|unpack(?:ing)?|execution chain|decompile|binary)\b",
            "逆向",
            "反编译",
            "样本",
            "执行链",
            "脱壳",
            "二进制",
        ],
    ),
    (
        "code-audit",
        [
            r"\b(code audit|source code|controller|handler|middleware|grep|taint|sink|entrypoint)\b",
            "源码",
            "审计",
            "入口",
            "控制器",
            "中间件",
            "危险函数",
            "信任边界",
        ],
    ),
    (
        "payload",
        [
            r"\b(payload|shellcode|staged|stageless|launcher|beacon)\b",
            "载荷",
            "启动器",
            "shellcode",
            "回连",
            "信标",
        ],
    ),
    (
        "cloud",
        [
            r"\b(aws|azure|gcp|iam|sts|role assumption|cloudtrail|metadata service)\b",
            "AWS",
            "Azure",
            "GCP",
            "IAM",
            "云凭证",
            "元数据服务",
        ],
    ),
    (
        "container",
        [
            r"\b(kubernetes|k8s|helm|container|docker|pod|namespace|hostpath|privileged)\b",
            "K8S",
            "容器",
            "集群",
            "逃逸",
            "Pod",
        ],
    ),
    (
        "network",
        [
            r"\b(http/2|websocket|ws|request smuggling|dns rebinding|protocol|tcp|udp|packet|pcap)\b",
            "协议",
            "流量",
            "抓包",
            "请求走私",
            "WebSocket",
            "DNS重绑定",
        ],
    ),
    (
        "crypto",
        [
            r"\b(rsa|aes|des|hash|sha|md5|padding oracle|lattice|cipher|stego)\b",
            "密码学",
            "加密",
            "哈希",
            "侧信道",
            "隐写",
        ],
    ),
    (
        "mobile",
        [
            r"\b(android|ios|apk|ipa|frida|objection|pinning|mobile)\b",
            "安卓",
            "苹果",
            "移动端",
            "证书锁定",
            "抓包",
        ],
    ),
    (
        "jailbreak",
        [
            r"\b(jailbreak|jail[\s-]?break|prompt injection|prompt inject|model bypass|safety bypass|content filter|refusal|guardrail|alignment bypass|unrestrict)\b",
            "越狱",
            "破限",
            "提示注入",
            "绕过限制",
            "绕过模型",
            "安全过滤",
            "模型限制",
            "内容过滤",
            "拒绝修复",
            "对齐绕过",
        ],
    ),
    (
        "evasion",
        [
            r"\b(edr|av|defender|waf|403|csp|bypass|sandbox)\b",
            "免杀",
            "绕过",
            "沙箱",
            "对抗",
            "WAF",
        ],
    ),
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
