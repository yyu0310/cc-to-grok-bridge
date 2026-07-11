# 04_Harness 參數表 — 給 cc-codex-bridge 複製用

> 目標：`cc-codex-bridge` = 複製本 repo → 填 **Codex 欄** → 改 adapter，不必重設計。  
> 最後更新：2026-07-11

## 總表

| 參數維度 | CC 現況 | Grok Build 做法 | Codex 欄（待填） |
|---|---|---|---|
| **config 家目錄** | `~/.claude/`（settings.json、hooks/、commands/）；`~/.claude.json`（MCP） | `~/.grok/`（config.toml、hooks/、skills/、memory/） | |
| **專案設定** | `<ws>/.claude/`、根 `CLAUDE.md` | `<ws>/.grok/`（rules、config、hooks）、根 `CLAUDE.md` 相容 | |
| **system prompt 載入** | 自動 `CLAUDE.md` / 專案規則 | `compat.claude` 載 `CLAUDE.md`；另 `.grok/rules/*.md`、可選 `AGENTS.md` | |
| **Grok/目標專用規則** | （無分離） | `.grok/rules/`（如 language.md）；**不**寫進 CLAUDE.md | |
| **skill 存放** | vault `SKILL/` → symlink `~/.claude/commands/*.md` | 原生掃 `~/.claude/commands`（compat）；亦可 `~/.grok/skills/<name>/SKILL.md` | |
| **skill 觸發** | `/name` slash + 模型自動 | 同 slash；`user-invocable` frontmatter | |
| **skill 格式** | 可 flat `.md` + YAML frontmatter | flat commands 相容；正式 skill 要目錄+`SKILL.md` | |
| **hooks 設定** | `~/.claude/settings.json` → `hooks` | `~/.grok/hooks/*.json`；可掃 CC settings（本橋關 `compat.claude.hooks` 改跑 adapter 包） | |
| **hooks 事件** | PreToolUse / PostToolUse / UserPromptSubmit / Stop / SubagentStop … | 同名事件 + 更多（SessionStart、PreCompact…） | |
| **hooks matcher 工具名** | `Bash` `Read` `Write` `Edit` … | 真名 `run_terminal_command` 等；**matcher 別名**對齊 CC | |
| **hooks stdin** | `tool_name` + `tool_input`（snake） | 文件示例 `toolName` + `toolInput`；adapter 正規化 | |
| **hooks 拒絕** | exit `2` + **stderr** 理由 | stdout `{"decision":"deny","reason"}` 或 exit 2；adapter 翻譯 | |
| **memory 路徑** | `~/.claude/projects/<hash>/memory/` | `~/.grok/memory/`（全域 MEMORY.md + `<slug>-<hash8>/`） | |
| **memory 載入** | 開場 MEMORY.md 200 行/25KB | **rules pointer 必載**；產品 search/index 可選 enable | |
| **memory 同步策略** | SoT | **單向 CC→Grok** `memory_sync.py`，CC 蓋同名檔 | |
| **MCP 設定位置** | `~/.claude.json` user/projects；claude.ai 雲端 connectors | `config.toml` `[mcp_servers.*]`；CLI `grok mcp` | |
| **MCP 遷移** | 四分類（key/OAuth/雲端/CLI） | 見 `docs/03_mcp.md`；key 人搬、雲端不可攜 | |
| **權限模型** | settings 允許清單 / ask | folder-trust、permission_mode、工具 approve UI | |
| **subagent** | Task / 內建 agent 類型 | `spawn_subagent`（explore/plan/general-purpose） | |
| **compat 開關** | — | `[compat.claude]` skills/rules/hooks/agents/mcps | |
| **bridge 安裝產物** | — | `~/.grok/hooks/cc-bridge-hooks.json`、`_cc_bridge_adapter.py` | |
| **doctor** | — | `scripts/bridge_doctor.py` | |
| **排程** | launchd 獨立 | 同（不綁 harness） | |

## 複製成 cc-codex-bridge 時的檢查清單

1. 複製 repo，改名與 README
2. 填上表 Codex 欄（官方文件 + 實測）
3. 重寫或分支 `hook_adapter.py`（stdin/deny 協定）
4. `install_bridge.py` 目標路徑改 `~/.codex/...`（或實際家目錄）
5. `memory_sync.py` 目標格式對齊 Codex memory
6. `docs/03_mcp.md` 改 Codex MCP config 形狀
7. doctor 路徑與全綠條件更新
8. **不動** CC 端 hooks/settings 本體

## 已知 Grok 實測錨點（2026-07-11）

- `/remember` 寫入 **`~/.grok/memory/MEMORY.md`（全域）**，不是 project 子目錄
- 專案鏡像放在 `~/.grok/memory/<slug>-<hash8>/`，hash = `sha256(workspace path)[:8]`（無 git origin）
- 敏感讀：Grok payload `target_file` + adapter + `block_sensitive_read.sh` → deny JSON（clasprc / .env）

標籤：#harness #codex #bridge
