# cc-to-grok-bridge

[English](README.md) | [繁體中文](README.zh-TW.md) | 简体中文

将 **Claude Code** 桥接到 **Grok Build**：共用规则／skill、用 adapter 跑同一套 hook 硬闸、可选 memory 镜像；Grok-only 不进入 Claude 上下文。

## 这是什么

| 层 | 桥做什么 |
|----|----------|
| System Prompt | 让 Grok 使用你已有的 workspace `CLAUDE.md`（compat 加载） |
| skill | 扫描你已有的 `~/.claude/commands`（slash／symlink） |
| hooks | 用一层转接器调用你原本的 Claude Code 安全脚本，并把「允许／拒绝」转成 Grok 能懂的格式（见下） |
| memory | CC→Grok pull + rules 指针 + 三区隔离；可选受限 push |
| plugins | **不自动**搬 CC `enabledPlugins`；always-on 见 [docs/06_plugins.md](docs/06_plugins.md)（原生 plugin 或 rules 备援） |
| MCP | 按**类型**由 AI 代装（永不自动抄 secret；见 AGENTS.md） |

## 兼容表

| 域 | 日用兼容 | 能怎么用 | 不是 100% 的地方 |
|----|----------|----------|------------------|
| **System Prompt** | **高** | 同一份 workspace `CLAUDE.md`（Grok compat 自动加载） | — |
| **skill** | **高** | 同一套 `~/.claude/commands`（含 symlink 到 skill 正文） | 少数 skill 缺 frontmatter 仍可用 slash；触发细节可能与 CC 不同 |
| **Hooks** | **高** | adapter + 你的 CC 脚本硬挡 | payload／deny 要转；没有完整 CC 式 ask UI |
| **Memory** | **高** | `memory_sync`、`.grok/rules/cc-memory-pointer`（开 workspace 就载）、三区、可选 `memory_push` | 与 CC 开场载 MEMORY.md 索引机制不同；产品 `memory_search` 是增强项 |
| **Plugins** | **中偏低** | **A** 有 Grok 包装才 `grok plugin install`（SessionStart always-on）；**B** 否则 always-on 规则进 `.grok/rules/`（开场自动载、免 slash） | CC 的 `enabledPlugins` + SessionStart **不会**自动过去；marketplace 不通；无 Grok adapter 时 A 未就绪 |
| **MCP** | **中** | 按类型重装（HTTP key、OAuth、stdio）；Notion／Google 见文档 | claude.ai **云端 connector 不可携**；secret 永不自动抄 |

**实测体感：** 把 CC 环境导入 **Grok Build**，通常比走 Antigravity／Gemini 桥顺很多（有真 hook 硬挡、memory 也比较好处理）。**Plugins always-on** 仍是明显落差，要单独处理。

Memory 补充：bridge 日用**不**要求先开 `[memory] enabled=true` 才载得到指针——**rules 指针**随项目加载。产品 memory 要搜索／注入再开即可。

Plugins 补充：CC 开了 auto plugin ≠ Grok 每 session 自动注入。详见 [docs/06_plugins.md](docs/06_plugins.md)。

MCP 补充：请 AI 按 [AGENTS.md](AGENTS.md) 装（含 Notion、Google、OAuth）。你负责浏览器点允许；**不要**默认让你手贴一大段 terminal。

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
| `docs/` | 差距矩阵、日用 SOP、memory、MCP、plugins、harness 表 |

## 安全

- 脚本永不复制 MCP env／token／OAuth
- 敏感读取硬挡：经 adapter + 你的 CC `block_sensitive_read`（如 `.clasprc*`、`.env`）
- Grok-only 规则在 `<workspace>/.grok/rules/`；本桥不应把它们写入 Claude 系统文件

## 限制

1. MCP：secret 不自动抄；claude.ai 云端 connector 不可携 — 见 [docs/03_mcp.md](docs/03_mcp.md)／[AGENTS.md](AGENTS.md)
2. Grok 全局 `~/.grok/memory/MEMORY.md`（`/remember`）≠ CC 项目 memory；sync 写项目子目录
3. 安装后需从 workspace 根重开 Grok session

## 许可

MIT — 见 [LICENSE](LICENSE)。
