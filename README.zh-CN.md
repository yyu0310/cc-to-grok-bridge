# cc-to-grok-bridge

[English](README.md) | [繁體中文](README.zh-TW.md) | 简体中文

将 **Claude Code** 桥接到 **Grok Build**：共用规则／skill、用 adapter 跑同一套 hook 硬闸、可选 memory 镜像；Grok-only 不进入 Claude 上下文。

## 这是什么

| 层 | 桥做什么 |
|----|----------|
| 规则／skill | 让 Grok 使用你已有的 `CLAUDE.md` 与 `~/.claude/commands` |
| hooks | 用一层转接器调用你原本的 Claude Code 安全脚本，并把「允许／拒绝」转成 Grok 能懂的格式（见下） |
| memory | 可选单向镜像：CC → Grok（`_from_cc`／`general`／`grok` 硬隔离） |
| MCP | 只提供迁移手册 — **永不**自动搬 API key／OAuth |

### hooks 转接器在干什么（白话）

Claude Code 的 hook 是一堆 shell 脚本（例如拦读 `.env`）。Grok 也会跑 hook，但两边约定不一样：

1. **送进脚本的 JSON 字段名不同**（payload 形状不同）
2. **「拦下来」时回给 UI 的格式也不同**（deny 协议不同）

所以不能把 CC 脚本原封不动当 Grok hook 用。中间那层薄程序叫 **adapter**（`scripts/hook_adapter.py`）：Grok 先调用它，它再去调你原本的 `~/.claude/hooks/*.sh`。

| 词 | 意思 |
|----|------|
| **薄 adapter** | 只做格式转换，不重写整套安全逻辑 |
| **包 CC hook 脚本** | 包一层再调用既有脚本；脚本本体仍是 CC 那份 |
| **payload 正规化** | 把 Grok 的字段名对成 CC 脚本看得懂的（例如 `target_file` → `file_path`） |
| **deny 翻译** | CC 拦下时常 `exit 2` + 错误信息；adapter 改成 Grok 认得的 `{"decision":"deny", …}` |

这样做的理由：

- **单一真相**：禁读规则仍只维护在 CC hook 里
- **Grok 也能硬挡**：不是只靠模型「记得不要读」，工具真的会被挡
- **不改 CC 脚本本体**：不用为了 Grok 去改 `~/.claude/hooks/*.sh`

## 需求

- macOS 或 Linux，Python 3.10+
- 已配置好的 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)（`~/.claude/hooks/`、`~/.claude/commands/`）
- [Grok Build](https://x.ai/) CLI／TUI
- 桥接脚本本身**不需要** API key

## 快速开始

```bash
git clone https://github.com/<YOUR_USERNAME>/cc-to-grok-bridge.git
cd cc-to-grok-bridge

# 你的真实 workspace 根（含 CLAUDE.md / .grok/ 的目录）
export CC_GROK_WORKSPACE=~/path/to/your-workspace

python3 scripts/install_bridge.py
python3 scripts/memory_sync.py --workspace "$CC_GROK_WORKSPACE"
python3 scripts/bridge_doctor.py --workspace "$CC_GROK_WORKSPACE"   # 应 fails=0
```

然后从该 workspace 启动 Grok，并重开 session 使 hooks 生效。

## 目录

| 路径 | 用途 |
|------|------|
| `scripts/hook_adapter.py` | Grok payload → CC hook；deny 翻译 |
| `scripts/install_bridge.py` | 安装 adapter 与 Grok hooks JSON；关闭双重触发 |
| `scripts/memory_sync.py` | CC → Grok memory pull |
| `scripts/memory_push.py` | 可选受限 push：`general/` → CC |
| `scripts/bridge_doctor.py` | 只读体检 + 硬挡冒烟测试 |
| `scripts/hook_acceptance.py` | adapter 层验收 |
| `architecture.md` | 架构不变量（「为什么」的单一真相） |
| `docs/` | 差距矩阵、日用 SOP、memory、MCP、harness 表 |

## 安全

- 脚本永不复制 MCP env／token／OAuth
- 敏感读取硬挡：经 adapter + 你的 CC `block_sensitive_read`（如 `.clasprc*`、`.env`）
- Grok-only 规则在 `<workspace>/.grok/rules/`；本桥不应把它们写入 Claude 系统文件

## 限制

1. MCP key／OAuth：人工；见 `docs/03_mcp.md`
2. claude.ai 云端 connectors 不可移植
3. Grok 全局 `MEMORY.md` ≠ CC 项目 memory；sync 写入项目子目录
4. 安装后需从 workspace 根重开 Grok session

## 许可

MIT — 见 [LICENSE](LICENSE)。
