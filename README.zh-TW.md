# cc-to-grok-bridge

[English](README.md) | 繁體中文 | [简体中文](README.zh-CN.md)

把 **Claude Code** 橋到 **Grok Build**：共用規則／skill、用 adapter 跑同一套 hook 硬閘、可選 memory 鏡像；Grok-only 不進 Claude 上下文。

## 這是什麼

| 層 | 橋做什麼 |
|----|----------|
| 規則／skill | 讓 Grok 吃你既有的 `CLAUDE.md` 與 `~/.claude/commands` |
| hooks | 薄 adapter 包 CC hook 腳本（payload 正規化 + deny 翻譯） |
| memory | 可選單向鏡像：CC → Grok（`_from_cc`／`general`／`grok` 硬隔離） |
| MCP | 只提供遷移手冊 — **永不**自動搬 API key／OAuth |

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
| `docs/` | 差距矩陣、日用 SOP、memory、MCP、harness 表 |

## 安全

- 腳本永不複製 MCP env／token／OAuth
- 敏感讀取硬擋：經 adapter + 你的 CC `block_sensitive_read`（如 `.clasprc*`、`.env`）
- Grok-only 規則在 `<workspace>/.grok/rules/`；本橋不應把它們寫進 Claude 系統檔

## 限制

1. MCP key／OAuth：人手；見 `docs/03_mcp.md`
2. claude.ai 雲端 connectors 不可攜
3. Grok 全域 `MEMORY.md` ≠ CC 專案 memory；sync 寫入專案子目錄
4. 安裝後需從 workspace 根重開 Grok session

## 授權

MIT — 見 [LICENSE](LICENSE)。
