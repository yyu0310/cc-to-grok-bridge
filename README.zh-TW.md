# cc-to-grok-bridge

[English](README.md) | 繁體中文 | [简体中文](README.zh-CN.md)

把 **Claude Code** 橋到 **Grok Build**：共用規則／skill、用 adapter 跑同一套 hook 硬閘、可選 memory 鏡像；Grok-only 不進 Claude 上下文。

## 這是什麼

| 層 | 橋做什麼 |
|----|----------|
| System Prompt | 讓 Grok 吃你既有的 workspace `CLAUDE.md`（compat 載入） |
| skill | 掃你既有的 `~/.claude/commands`（slash／symlink） |
| hooks | 用一層轉接器呼叫你原本的 Claude Code 安全腳本，並把「允許／拒絕」轉成 Grok 看得懂的格式（見下） |
| memory | CC→Grok pull + rules 指標 + 三區隔離；可選受限 push |
| plugins | **不自動**搬 CC `enabledPlugins`；always-on 見 [docs/06_plugins.md](docs/06_plugins.md)（Grok 原生 plugin 或 rules 備援） |
| MCP | 依**型態**由 AI 代裝（永不自動抄 secret；見 AGENTS.md） |

## 研究助手：ccgrok.sh

一支小 wrapper，把 `grok -p` 當成有紀律的研究工具。它會墊上一段與模型無關的研究方法前綴（[`research-prefix.md`](research-prefix.md)），並從一個乾淨的暫存目錄跑，讓純研究查詢不被專案規則污染。

```bash
scripts/ccgrok.sh "你的問題"
```

前綴會逼它給出附來源、附日期、事實與推測分離的答案，並且（同題實測）讓 Grok **主動標出過期或被降級的資訊**，而不是很篤定地講錯。同一份 `research-prefix.md` 對任何 headless AI CLI（`grok -p`、`agy -p`、`claude -p`）都適用。

唯讀 flag（`--disallowed-tools "run_terminal_cmd,write,search_replace"`）確保即使 auto-approve，這次執行也碰不到本地檔案。

## 相容表

| 域 | 相容性 | 能怎麼用 | 不是 100% 的地方 |
|----|--------|----------|------------------|
| System Prompt | 高 | 同一份 workspace CLAUDE.md（Grok compat 自動載入） | — |
| skill | 高 | 同一套 ~/.claude/commands（含 symlink） | 少數缺 frontmatter 仍可用；觸發細節可能不同 |
| Memory | 高 | memory_sync + rules 指標 + 三區隔離；可選 memory_push | 與 CC 載 MEMORY.md 索引機制不同；產品搜尋是加強項 |
| Hooks | 中 | adapter + 你的 CC 腳本硬擋 | payload／deny 要轉；無完整 CC 式 ask UI |
| MCP | 中 | 依型態重裝（HTTP key、OAuth、stdio）；Notion／Google 見文檔 | claude.ai 雲端 connector 不可攜；secret 永不自動抄 |
| Plugins | 低 | A：有 Grok 包裝再 install；B：rules always-on（見補充） | CC 設定不會自動過去；marketplace 不相通 |

**實測體感：** 把 CC 環境導入 **Grok Build**，通常比走 Antigravity／Gemini 橋順很多（有真 hook 硬擋、memory 也比較好處理）。Plugins always-on 仍是明顯落差，要單獨處理。

**Plugins 補充（相容性標「低」＝不能 drop-in，但表內／文檔有解法）：**  
CC 開了 auto plugin ≠ Grok 每 session 自動注入。路線 **A**：上游有 Grok 包裝才 `grok plugin install`（SessionStart always-on）；**B**：否則把 always-on 規則放進 `.grok/rules/`（開場自動載、免 slash）。無 Grok adapter 時不能當原生 plugin 裝。詳見 [docs/06_plugins.md](docs/06_plugins.md)。  
**展望：** 若多數常用 plugin 都上 Grok marketplace（有正式 Grok 包裝），相容性可升到 **中～高**（仍非 100% 自動搬 CC 設定，但 A 會變常態、B 只當例外）。

Memory 補充：bridge 日用**不**要求先開 `[memory] enabled=true` 才載得到指標——**rules 指標**隨專案載入。產品 memory 要搜尋／注入再開即可。

MCP 補充：請 AI 照 [AGENTS.md](AGENTS.md) 裝（含 Notion、Google、OAuth）。你負責瀏覽器按允許；**不要**預設叫你手貼一大段 terminal。

### hooks 轉接器在幹嘛（白話）

Claude Code 的 hook 是一堆 shell 腳本（例如擋讀 `.env`）。Grok 也會跑 hook，但兩邊約定不一樣：

1. **送進腳本的 JSON 欄位名不同**（payload 形狀不同）
2. **「擋下來」時要回給 UI 的格式也不同**（deny 協議不同）

所以不能把 CC 腳本原封不動當 Grok hook 用。中間那層薄程式叫 **adapter**（`scripts/hook_adapter.py`）：Grok 先呼叫它，它再去叫你原本的 `~/.claude/hooks/*.sh`。

| 詞 | 意思 |
|----|------|
| **薄 adapter** | 只做格式轉換，不重寫整套安全邏輯 |
| **包 CC hook 腳本** | 包一層再呼叫既有腳本；腳本本體仍是 CC 那份 |
| **payload 正規化** | 把 Grok 的欄位名對成 CC 腳本看得懂的（例如 `target_file` → `file_path`） |
| **deny 翻譯** | CC 擋下時常 `exit 2` + 錯誤訊息；adapter 改成 Grok 認得的 `{"decision":"deny", …}` |

這樣做的理由：

- **單一真相**：禁讀規則仍只維護在 CC hook 裡
- **Grok 也能硬擋**：不是只靠模型「記得不要讀」，工具真的會被擋
- **不改 CC 腳本本體**：不用為了 Grok 去改 `~/.claude/hooks/*.sh`

## 需求

- macOS 或 Linux，Python 3.10+
- 已設定好的 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)（`~/.claude/hooks/`、`~/.claude/commands/`）
- [Grok Build](https://x.ai/) CLI／TUI
- 橋接腳本本身**不需要** API key

## 快速開始

```bash
git clone https://github.com/<YOUR_USERNAME>/cc-to-grok-bridge.git
cd cc-to-grok-bridge

# 你的真實 workspace 根（有 CLAUDE.md / .grok/ 的那個資料夾）
export CC_GROK_WORKSPACE=~/path/to/your-workspace

python3 scripts/install_bridge.py
python3 scripts/memory_sync.py --workspace "$CC_GROK_WORKSPACE"
python3 scripts/bridge_doctor.py --workspace "$CC_GROK_WORKSPACE"   # 應 fails=0
```

然後從該 workspace 開 Grok，並重開 session 讓 hooks 生效。

## 目錄

| 路徑 | 用途 |
|------|------|
| `scripts/hook_adapter.py` | Grok payload → CC hook；deny 翻譯 |
| `scripts/install_bridge.py` | 掛 adapter 與 Grok hooks JSON；關雙重觸發 |
| `scripts/memory_sync.py` | CC → Grok memory pull |
| `scripts/memory_push.py` | 可選受限 push：`general/` → CC |
| `scripts/bridge_doctor.py` | 唯讀健檢 + 硬擋煙測 |
| `scripts/hook_acceptance.py` | adapter 層驗收 |
| `architecture.md` | 架構不變量（「為什麼」的單一真相） |
| `docs/` | 差距矩陣、日用 SOP、memory、MCP、plugins、harness 表 |

## 安全

- 腳本永不複製 MCP env／token／OAuth
- 敏感讀取硬擋：經 adapter + 你的 CC `block_sensitive_read`（如 `.clasprc*`、`.env`）
- Grok-only 規則在 `<workspace>/.grok/rules/`；本橋不應把它們寫進 Claude 系統檔

## 限制

1. MCP：secret 不自動抄；claude.ai 雲端 connector 不可攜 — 見 [docs/03_mcp.md](docs/03_mcp.md)／[AGENTS.md](AGENTS.md)
2. Grok 全域 `~/.grok/memory/MEMORY.md`（`/remember`）≠ CC 專案 memory；sync 寫專案子目錄
3. 安裝後需從 workspace 根重開 Grok session

## 授權

MIT — 見 [LICENSE](LICENSE)。
