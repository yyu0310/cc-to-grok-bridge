# Grok Build · Hook 驗收報告（adapter 層）

> 對照：你自己的 Claude Code hook 文檔  
> 日期：2026-07-11（晚間完整重跑）  
> 再開：2026-07-11 開源脫敏後全數重跑 — 本體與開源 scripts 皆 **22/22 PASS** + doctor fails=0（含 `--with-clasp` 真 push）  
> 開源版：路徑已泛化；全數 QA 請設 `CC_GROK_WORKSPACE`／可選 `CC_GROK_CLASP_SANDBOX`

## 環境

| 項 | 值 |
|----|-----|
| workspace | `~/path/to/your-workspace` |
| adapter | `~/.grok/hooks/_cc_bridge_adapter.py` → 本 repo `scripts/hook_adapter.py` |
| bridge JSON | `~/.grok/hooks/cc-bridge-hooks.json` |
| compat | `[compat.claude] hooks = false` |
| 腳本本體 | `~/.claude/hooks/*.sh`（未改） |
| 產品 memory | 可選；bridge 日用主靠 rules pointer（本機環境可能已 enable） |
| 驗收腳本 | `scripts/hook_acceptance.py` |
| doctor | `scripts/bridge_doctor.py` → **全綠** |

## 方法

1. **批次**：`python3 scripts/hook_acceptance.py [--with-clasp]`  
   經 adapter 餵 Grok 形 payload；敏感路徑只在腳本內用 `Path` 組裝（避免外層 bash-gate 誤擋驗收指令）。  
2. **doctor**：安裝完整性、memory 三區、adapter 單元煙測。

判定：expect deny → exit 2 或 `decision=deny`；expect allow → 非 deny；Post／lifecycle → exit 0。

## 結果（2026-07-11 重跑 **22/22 PASS**）

### A. 原 14 支 CC 橋接主線（摘要）

| # | 事件 | 腳本／案例 | 結果 |
|---|------|------------|------|
| 1 | PreToolUse | memory_write_gate 非 memory 路徑 | ✅ PASS allow |
| 2 | PreToolUse | block_sensitive_read → clasprc | ✅ PASS deny |
| 2b | 同上 | CLAUDE.md | ✅ PASS allow |
| 2c | 同上 | `.env` 路徑 | ✅ PASS deny |
| 3 | PreToolUse | bash_security_gate `echo` | ✅ PASS allow |
| 4 | PreToolUse | pre_push_safety 非 push | ✅ PASS allow |
| 5–6 | Post | auto_clasp 非 .gs skip；auto_qa 暫存 .py | ✅ PASS |
| 7 | Pre | CC memory_write_gate 第一次寫 CC memory 路徑 | ✅ PASS deny |
| 8–9 | lifecycle | tool_guide / commitment Stop | ✅ PASS |
| 10 | UserPrompt | 時間注入（bridge command） | ✅ PASS 含 `Current time: …` |
| — | doctor | clasprc / .env / CLAUDE 單元 | ✅ 全綠 |

（完整 14 事件註冊仍見 bridge JSON；上表為本輪腳本實際斷言項。）

### B. 本輪新增／修補項

| # | 案例 | 結果 |
|---|------|------|
| A1 | adapter 透傳 `additionalContext`（時間字串） | ✅ PASS（修前會被改成只剩 allow） |
| A2 | adapter：`permissionDecision=deny` → Grok `decision=deny` | ✅ PASS |
| A3 | adapter：`permissionDecision=ask` → Grok allow + stderr 理由 | ✅ PASS（Grok 無 CC 式 ask 視窗） |
| G1 | `grok_memory_write_gate` 第 1 次 deny | ✅ PASS |
| G2 | 同 session 第 2 次 ask→allow | ✅ PASS |
| G3 | `_from_cc/*` 手寫 deny | ✅ PASS |
| C1 | clasp-run-sandbox **真** `clasp push`（`--with-clasp`） | ✅ PASS `Pushed 2 files` |
| M1 | 產品 memory `enabled=true` | ✅ 已開 |

### C. 仍屬 TUI 肉眼（不阻擋日用／開源）

| 項 | 狀態 |
|----|------|
| 時間字串是否進**模型 context** | adapter 已透傳；Grok 被動 hook 是否注入需 TUI 問「現在幾點」 |
| `/remember` UI 是否繞過 PreToolUse | 產品路徑，與 agent Write 閘門分開 |
| pre_push 真攔截假 key | 需 bare repo 劇本（見 CC hook.md） |

## 重跑

```bash
cd /path/to/cc-to-grok-bridge
export CC_GROK_WORKSPACE=~/path/to/your-workspace
python3 scripts/bridge_doctor.py --workspace "$CC_GROK_WORKSPACE"
python3 scripts/hook_acceptance.py
# 可選真 clasp：export CC_GROK_CLASP_SANDBOX=… 後再 --with-clasp
python3 scripts/hook_acceptance.py --with-clasp
```

標籤：#smoke #hooks #grok
