# Codex Red Team Opt-In Mode

> **Normal by default. Offensive only when explicitly armed.**

A lightweight, phase-aware Codex profile for offensive work.  
It keeps the assistant in **normal mode** by default and only activates **red-team routing** when the user explicitly turns it on.

## Highlights

- **Opt-in only** red-team mode
- **Structured JSON state**
- **Modular hooks**
- **Cross-platform installer**
- **Validation + tests**
- **Per-phase playbooks**
- **Low-noise / OPSEC-aware guidance**

## Quick Start

### Enable red-team mode

```text
进入红队模式
开启红队模式
/redteam on
enable red team mode
```

### Disable red-team mode

```text
退出红队模式
关闭红队模式
/redteam off
disable red team mode
```

### Install

```bash
python scripts/install.py
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

## Repository Layout

```text
codex/
  AGENTS.md
  hooks/
    session-start-context.py
    hook-security-context-hook.py
    redteam_state.py
    core/
agents/
  skills/
    red-team-command-doctrine/
      SKILL.md
      references/
docs/
scripts/
tests/
.github/
```

渗透测试（Authorized Penetration Testing）和安全研究使用。**

### 重要声明
- 本工具 **仅限** 在您拥有 **明确书面授权** 的目标系统或环境中使用。
- 未经授权擅自用于任何生产系统、他人资产或非授权目标，属于违法行为，作者及贡献者不承担任何责任。
- 使用本项目即表示您同意自行承担所有风险，包括但不限于法律责任、数据泄露、系统损坏等后果。
- 作者及本项目不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权。

### Legal & Ethical Use Only
This project is intended **solely for educational purposes, authorized red team operations, and legal penetration testing** where you have explicit permission from the system owner.

- Any unauthorized use, including but not limited to attacking systems without consent, is strictly prohibited.
- The authors and contributors assume **no liability** for any damages, legal consequences, or losses resulting from the use or misuse of this tool.
- Users are fully responsible for ensuring their activities comply with all applicable local, national, and international laws.

**继续使用本项目 = 您已阅读、理解并同意以上全部条款。**

---

**如果您无法确保合法授权，请立即停止使用本项目。**
