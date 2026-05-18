from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Iterable

PHASE_EXAMPLES: dict[str, list[str]] = {
    "web": ["trace one exploit path through requests parameters session state and hidden endpoints", "review burp traffic and determine whether this web issue is exploitable", "analyze this login flow token reuse and authorization boundary", "梳理这个登录接口和鉴权边界，判断 token 是否可复用", "基于 burp 流量分析一条可验证的 web 利用路径"],
    "ad": ["reason about kerberos delegation acl abuse and lateral movement in active directory", "identify the next quiet step in a windows domain attack chain", "分析域内委派、票据与 ACL 关系，找一条低噪声推进路径"],
    "postex": ["triage a foothold for privilege escalation credential reuse and next-hop value", "evaluate what to do after code execution on a host", "已经拿到 shell，下一步应该如何做主机分诊、提权和横向准备"],
    "reverse": ["recover the execution chain of a binary loader or malware sample", "analyze unpacking configuration extraction process launch sequence and binary logic", "这个程序会释放资源并拉起子进程，帮我梳理执行链"],
    "code-audit": ["trace one controllable input to a dangerous sink across handlers middleware and trust boundaries", "review source code for auth permission logic hidden trust shortcuts and a precise proof path", "从入口一路追到危险函数，看看权限边界哪里失守"],
    "payload": ["choose payload shape launcher format staged versus stageless tradeoffs and delivery constraints", "compare delivery formats and operator tradeoffs for an implant or launcher", "帮我在 staged 和 stageless 之间做取舍并说明约束条件"],
    "evasion": ["plan av edr waf or sandbox bypass techniques with low-noise tradeoffs", "evaluate defender bypass options and operational constraints", "评估这个 WAF/403 场景下的最小验证绕过路径"],
    "cloud": ["analyze aws iam role assumption privilege boundaries and metadata exposure", "review cloud identity paths and abuse opportunities in the control plane", "分析云 IAM 权限、元数据与凭证滥用路径"],
    "container": ["reason about kubernetes pod escape hostpath abuse and cluster privilege boundaries", "review container breakout paths and namespace isolation issues", "分析容器逃逸和 kubernetes 集群权限边界"],
    "network": ["assess request smuggling websocket or protocol parsing issues from packet traces", "reason about dns rebinding and protocol attack paths", "基于抓包和协议行为分析请求走私或协议攻击路径"],
    "crypto": ["analyze rsa hash or symmetric cipher weaknesses and attack conditions", "review the challenge from a crypto attack perspective", "从密码学角度分析 RSA、哈希或对称加密的利用条件"],
    "mobile": ["analyze an android apk or ios ipa for pinning bypass and mobile attack surface", "review a mobile application from frida objection and ssl pinning angles", "分析安卓或 iOS 应用的抓包、证书锁定与移动端攻击面"],
}

TOKEN_RE = re.compile(r"[a-z0-9_./-]+|[\u4e00-\u9fff]")

def _normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _char_ngrams(token: str, n: int = 3) -> Iterable[str]:
    if len(token) <= n:
        yield token
        return
    for i in range(len(token) - n + 1):
        yield token[i : i + n]

def _tokenize(text: str) -> list[str]:
    normalized = _normalize(text)
    pieces = TOKEN_RE.findall(normalized)
    tokens: list[str] = []
    for piece in pieces:
        if re.fullmatch(r"[\u4e00-\u9fff]", piece):
            tokens.append(piece)
            continue
        tokens.append(piece)
        tokens.extend(_char_ngrams(piece))
    return tokens

def _vectorize(text: str) -> Counter[str]:
    return Counter(_tokenize(text))

def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)

@lru_cache(maxsize=1)
def _phase_prototypes() -> dict[str, Counter[str]]:
    return {phase: _vectorize(" ".join(examples)) for phase, examples in PHASE_EXAMPLES.items()}

def classify_phase_semantically(prompt: str) -> tuple[str | None, float]:
    query = _vectorize(prompt)
    best_phase: str | None = None
    best_score = 0.0
    for phase, proto in _phase_prototypes().items():
        score = _cosine(query, proto)
        if score > best_score:
            best_phase = phase
            best_score = score
    return best_phase, best_score
