# cc-to-grok-bridge — Architecture

> 給未來的維護者／任一 AI：這份是 **單一真相來源的架構說明**。  
> 實作細節分散在 `docs/*` 與 `scripts/*`；衝突時以本檔的「不變量」為準。  
> 最後更新：2026-07-11

---

## 0. 一句話

**Claude Code（CC）是制度與腳本的本尊；Grok Build 是來賓。**  
橋做三件事：讓 Grok **讀得到** CC 的規則與 skill、**跑得了** 同一套 hook 硬閘、**可選地鏡像** memory——且 **Grok 特有的東西永不塞進 Claude 的上下文**。

---

## 1. 設計目標與非目標

### 1.1 目標

| # | 目標 |
|---|------|
| G1 | 從你的 workspace 根目錄開 Grok，體感接近 CC（規則、skill、硬閘） |
| G2 | 單一真相：skill 正文、hook **腳本**、CLAUDE.md 只維護一份 |
| G3 | 動態「拉」：Grok 開場自動把 CC→Grok 該更新的東西更新掉（fail-open） |
| G4 | 可審計、可回滾、doctor 可驗 |
| G5 | **上下文隔離**：Grok-only rules／memory **不進入** Claude 開場載入 |

### 1.2 非目標

| # | 非目標 |
|---|--------|
| N1 | 不把 Grok 變成第二套完整 AI 系統（不複製 47 個 skill 正文） |
| N2 | 不自動搬 MCP API key／OAuth token |
| N3 | 不默認把 Grok 寫的東西灌回 CC memory（見 §6） |
| N4 | 不修改 `~/.claude/hooks/*.sh` 本體來「遷就」Grok（用 adapter 包） |
| N5 | 本 repo 不負責 push 上 GitHub（另走開源流程） |

---

## 2. 上下文隔離（回答「不要佔用 Claude 上下文」）

### 2.1 Claude 開場會吃什麼？

CC 典型會載入：

- `CLAUDE.md`（vault 根）
- `~/.claude/projects/<hash>/memory/MEMORY.md` 開頭一段（約 200 行／25KB 上限）
- hooks／skills 依機制觸發（skill 不是整包塞進每句，但 memory 索引會）

### 2.2 Grok 開場會吃什麼？

- 同上 `CLAUDE.md`（compat，**同一檔**——這是**刻意共享**的核心指令）
- **僅 Grok**：`<workspace>/.grok/rules/*.md`
- 可選：Grok memory 索引／搜尋結果（`~/.grok/memory/**`）
- bridge hooks（執行層，不佔「規則正文」token，但會在工具呼叫時跑）

### 2.3 隔離規則（不變量）

```
┌─────────────────────────────────────────────────────────┐
│  SHARED（兩邊都該遵守）                                    │
│  • CLAUDE.md                                            │
│  • AI 系統總管理/SKILL/*  （經 symlink）                   │
│  • ~/.claude/hooks/*.sh   （Grok 經 adapter 呼叫，不改檔） │
└─────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│ Claude 上下文         │    │ Grok 上下文                   │
│ • 上列 SHARED         │    │ • 上列 SHARED                 │
│ • CC memory 索引      │    │ • .grok/rules/* （Grok-only） │
│ • 绝不自动吃：        │    │ • ~/.grok/memory/**           │
│   .grok/rules         │    │ • 不把 Grok-only 寫進         │
│   ~/.grok/**          │    │   CLAUDE.md / CC memory 源    │
└──────────────────────┘    └──────────────────────────────┘
```

**實作對照：**

| 東西 | 放哪 | Claude 會不會吃到 |
|------|------|-------------------|
| 繁中／反共匪用語偏好 | `.grok/rules/language.md` | **否** |
| 禁止動 CC 系統檔 | `.grok/rules/00_cc_system_boundary.md` | **否** |
| memory 路徑指標 | `.grok/rules/cc-memory-pointer.md` | **否** |
| CC→Grok 鏡像全文 | `~/.grok/memory/VS-Project-*/` | **否**（除非有人再 push 進 CC） |
| 共享核心 | `CLAUDE.md` | **是**（兩邊都要） |

> 「Grok 特有 rule／memory 不佔 Claude 上下文」＝ **只寫進 `.grok/` 與 `~/.grok/`，永不寫進 CLAUDE.md，且未核准前不 push 進 CC memory 源。**

---

## 3. 系統元件圖

```
                    ┌──────────────────┐
                    │  AI 系統總管理     │
                    │  SKILL/  hook文檔  │
                    │  harness 制度     │
                    └────────┬─────────┘
                             │ 正文／制度
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌──────────────┐  ┌─────────────────────┐
│ CLAUDE.md       │  │ ~/.claude/   │  │ ~/.claude/hooks/*.sh│
│ (SHARED rules)  │  │ commands/*   │  │ (真・硬閘腳本)        │
└────────┬────────┘  │ → symlink    │  └──────────┬──────────┘
         │           └──────┬───────┘             │
         │ 相容載入          │ 相容掃 skill         │ 僅被呼叫
         ▼                  ▼                     ▼
┌────────────────────────────────────────────────────────────┐
│                     Grok Build                              │
│  rules: .grok/rules/*     hooks: ~/.grok/hooks/*.json       │
│  memory: ~/.grok/memory/* adapter → 呼叫 CC 腳本            │
│  config: ~/.grok/config.toml  [compat.claude] hooks=false   │
└────────────────────────────────────────────────────────────┘
         ▲
         │ scripts
┌────────┴────────┐
│ cc-to-grok-bridge│
│ install / adapter│
│ memory_sync/pull │
│ doctor           │
└─────────────────┘
```

---

## 4. 目錄與產物清單

### 4.1 Bridge repo（工具與文檔）

```
cc-to-grok-bridge/
  architecture.md          ← 本檔
  README.zh-TW.md          ← 使用與 Battle-tested
  docs/
    00_差距矩陣.md
    01_絲滑啟動.md
    02_memory.md
    03_mcp.md
    04_harness_參數表.md
    05_dynamic_bidirectional_sync.md
  scripts/
    hook_adapter.py        ← stdin 正規化 + deny 翻譯
    install_bridge.py      ← 生成 Grok hooks JSON
    memory_sync.py         ← CC memory → Grok 鏡像（單向 pull 檔）
    bridge_pull.py         ← 動態拉：sync + stale install
    install_session_pull_hook.py
    bridge_doctor.py       ← 健檢
```

### 4.2 執行期（機器上）

| 路徑 | 誰寫 | 用途 |
|------|------|------|
| `~/.grok/hooks/cc-bridge-hooks.json` | install_bridge | 包裝後的 Pre/Post hooks |
| `~/.grok/hooks/_cc_bridge_adapter.py` | symlink→repo | 適配器 |
| `~/.grok/hooks/cc-bridge-session-pull.json` | install_session_pull | SessionStart → bridge_pull |
| `~/.grok/config.toml` `[compat.claude] hooks=false` | install | 避免與 bridge 雙跑 |
| `~/.grok/config.toml` `[memory]` | 可選 | Grok 產品 memory；**與 CC 上下文無關** |
| `~/.grok/memory/VS-Project-<hash8>/` | memory_sync | CC 的 **鏡像**（副本） |
| `~/.grok/memory/MEMORY.md` | Grok `/remember` | Grok **全域**小記；**不要**當 CC 索引覆寫目標 |
| `<ws>/.grok/rules/*.md` | 人／腳本 | **Grok-only** 規則 |

### 4.3 明確不碰（CC 系統）

見 `.grok/rules/00_cc_system_boundary.md`：`CLAUDE.md`、`~/.claude/settings*.json`、`~/.claude.json`、`hooks/*.sh`、`commands/*`、CC memory **源**（預設禁寫）。

---

## 5. 各子系統運作原理

### 5.1 System prompt／規則

```
Grok session start
  → 載入 CLAUDE.md          （SHARED）
  → 載入 .grok/rules/*.md   （Grok-only，不進 CC）
  → （不載入）AGENTS.md 除非你自己建
```

### 5.2 Skills

```
vault SKILL/**/*.md
  --symlink--> ~/.claude/commands/<name>.md
                    │
                    ├─ Claude: /name
                    └─ Grok:   同路徑被 compat 掃到 → /name
```

- **已是「即時共享」**：改 vault 檔，兩邊下次觸發都是新內容。  
- **不必**再做 skill 檔案同步 job。

### 5.3 Hooks（最關鍵）

**問題：**  
CC hook 吃 `tool_name` + `tool_input.file_path` + exit 2 + stderr。  
Grok 可能送 `toolName` + `toolInput.target_file` + 要 deny JSON。

**解法：**

```
Grok PreToolUse
  → 讀 ~/.grok/hooks/cc-bridge-hooks.json
  → 執行: python3 adapter.py /path/to/cc_hook.sh
       adapter:
         1. 讀 stdin JSON
         2. 正規化成 CC 慣用鍵與工具別名
         3. 管道給真正的 .sh
         4. 若 exit 2 → stdout {"decision":"deny","reason":...}
```

**為何 `compat.claude.hooks = false`？**

- Grok **也能**直接掃 `~/.claude/settings.json` 的 hooks。  
- 若同時再跑 bridge JSON → **同一腳本觸發兩次**。  
- 故：關「直接掃 CC settings」，只跑「已包 adapter 的 bridge JSON」。  
- **沒有改壞** CC：CC 自己開 session 仍讀自己的 settings，與這旗標無關。

**Hooks 資料流（動態）：**

```
[~/.claude/settings.json 變更]
        │ mtime 更新
        ▼
[bridge_pull / install --if-stale]
        │ 重讀 settings，重包 command 字串
        ▼
[~/.grok/hooks/cc-bridge-hooks.json 更新]
        │
        ▼
[下一次 Grok 工具呼叫使用新包裝]
```

### 5.4 Memory（見 §6 策略）

**目前實作（靜態 + 動態 pull）：**

```
CC: ~/.claude/projects/<path-hash>/memory/*.md
        │ memory_sync.py（覆寫同名檔；CC 贏）
        ▼
Grok 鏡像: ~/.grok/memory/<slug>-<hash8>/*.md
        │
        +→ 寫 .grok/rules/cc-memory-pointer.md（短指標，Grok-only）

SessionStart → bridge_pull.py → memory_sync + maybe install
```

**鏡像是副本，不是讓 Claude 多載一份。** Claude 仍只載自己的 memory 源。

### 5.5 MCP

- 文檔：`docs/03_mcp.md` 四分類。  
- 腳本 **永不**複製 env/token。  
- doctor 只列 **名稱**。  
- 與「動態同步」脫鉤：人搬 key。

---

## 6. Memory 策略：General vs Grok-specific（建議定案）

### 6.1 你的直覺（對）

> 分成 general 與 grok-specific；只把 general 同步到 CC；Grok 寫入要打標。

這方向正確，但要補三層，否則不夠全面：

### 6.2 建議的完整模型（三層，不是兩層）

| 層 | 名稱 | 內容範例 | 存哪 | 同步 |
|----|------|----------|------|------|
| **L0 Shared rules** | 核心指令 | 資安、協作、路由 | `CLAUDE.md` | 本來就共享；**不用 memory 同步** |
| **L1 General memory** | 跨 harness 都該記得的「事實／決策／指標」 | 「hepta 只能走白名單腳本」「工單在某路徑」 | CC memory 為 SoT；Grok 鏡像 pull | **CC → Grok 常態 pull**；Grok→CC 僅 **tagged general + 審核** |
| **L2 Grok-specific** | 只服務 Grok 產品／橋 | 繁中偏好、adapter 行為、Grok UI、bridge 除錯 | `.grok/rules/*` 或 `~/.grok/memory/…/grok/` 或 frontmatter `harness: grok` | **禁止進 Claude 上下文**（不寫 CLAUDE、不 push CC） |

> 「標籤」打在 **L1 由 Grok 產出、可能回寫 CC** 的條目上；L2 根本不走 push。

### 6.3 標籤契約（建議 frontmatter）

Grok 若寫可共享筆記，檔頭：

```markdown
---
source: grok-build
harness: shared          # shared | grok
scope: general           # general | grok-specific
synced_to_cc: false      # push 成功後改 true
updated: 2026-07-11
---
```

- `harness: grok` 或 `scope: grok-specific` → **push 過濾器丟棄**  
- `harness: shared` + `scope: general` → 才進入「候選 push 佇列」  
- push 時在 CC 檔 **保留** `source: grok-build`，讓之後 CC／人知道來源

### 6.4 方向性（謹慎版定案）

| 方向 | 現在 | 建議 |
|------|------|------|
| **CC → Grok** | 已做 full mirror | 維持；SessionStart pull。這是「Grok 看得懂你的世界」 |
| **Grok → CC** | **`memory_push.py` 已開** | 只掃 `general/*.md`；打 `source: grok-build`；MEMORY.md 紅線內加一行；`grok/` 永不 push |
| Grok `/remember` 全域檔 | 寫 `~/.grok/memory/MEMORY.md` | 視為 **L2 或未分類**；**禁止**整包灌 CC MEMORY.md（會爆紅線、污染索引） |

**回答「要不要讓 Grok memory 同步至 CC」：**  
- **現在：不要自動同步過去。**  
- **策略上：可以，但只限 L1 general + 標籤 + 審核閘；L2 永遠留下 Grok。**  
- 你提的分法 **夠當主軸**；補上 L0／標籤契約／禁止灌全域 MEMORY／CC 紅線，才算全面。

### 6.5 還要考慮的邊界（全面性檢查清單）

| 風險 | 對策 |
|------|------|
| 雙寫衝突 | CC 贏 pull；push 僅新增 topic 或明確 append 區 `## From Grok` |
| CC MEMORY 25KB 紅線 | push **禁止**塞主索引；只加 topic 檔 + 一行指標 |
| 秘密進 memory | push 前掃 `.env`/key pattern；命中 abort |
| 迴圈 | pull 不吃 `source: grok-build` 剛 push 回去又鏡像——可接受；但不要 Grok 再「智能改寫」後 push |
| 模型亂打標 | push 腳本 **白名單目錄** 比 frontmatter 更硬：`memory/general/` vs `memory/grok/` |
| 目錄硬隔離（推薦） | 見下 |

### 6.6 推薦目錄硬隔離（比純標籤更穩）

```
~/.grok/memory/VS-Project-xxx/
  _from_cc/           # pull 進來的純鏡像（唯讀心智：可被 pull 覆蓋）
  general/            # Grok 寫的、允許候選 push → CC
  grok/               # Grok-only，永不 push
  MEMORY.md           # 可為「指標」：鏈到三區；或保留 CC 鏡像索引
```

比「整包 mirror 混寫」更不易誤 push。  
**遷移：** 下一迭代改 `memory_sync` 寫入 `_from_cc/`，新寫入走 `general/`|`grok/`。

### 6.7 與「不佔 Claude 上下文」的對齊

- L2 與 `.grok/rules` → Claude **零**載入  
- L1 push 成功 → **會**進 Claude 下次 memory 索引 → 這是你**故意**要共享的 general，不是污染  
- 因此 push 必須保守，才不會把 Grok 廢話塞爆 CC 開場 token

---

## 7. 動態同步流程（現行 + 目標）

### 7.1 現行：SessionStart pull

```
Grok SessionStart
  → hook: cc-bridge-session-pull.json
  → python3 bridge_pull.py --workspace ~/path/to/your-workspace
       ├─ memory_sync.py      # CC → 鏡像（CC 蓋同名）
       └─ if settings.json mtime > bridge json:
              install_bridge.py   # 重包 hooks
  → 失敗只 log，不擋開場（fail-open）
```

### 7.2 目標：完整狀態機

```
                    ┌─────────────┐
                    │  idle       │
                    └──────┬──────┘
           SessionStart    │    CC settings mtime↑
           / 定時 pull     │    / 手動 bridge_pull
                           ▼
                    ┌─────────────┐
                    │  pulling    │
                    │  CC→Grok    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      memory mirror   hooks rewrap    doctor(opt)
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                    ┌─────────────┐
                    │  ready      │
                    └──────┬──────┘
                           │ 用戶明示 push general
                           ▼
                    ┌─────────────┐
                    │  pushing*   │  *未實作：dry-run→gate→CC topic
                    └─────────────┘
```

### 7.3 觸發矩陣

| 事件 | 動作 | 實作狀態 |
|------|------|----------|
| Grok SessionStart | pull memory + stale install | ✅ |
| 手動 `bridge_pull.py` | 同上 | ✅ |
| CC 改 settings hooks | 下次 pull／--if-stale 重包 | ✅ |
| CC 改 skill 正文 | 無需同步（symlink） | ✅ 天生 |
| Grok 寫 general memory | 候選 push | ❌ 未做 |
| launchd 每日 | pull | ❌ 模板可後補 |
| MCP key | 人 | 文檔 only |

---

## 8. 安全模型

| 層 | 機制 |
|----|------|
| 禁讀 | CC `block_sensitive_read.sh` 等，經 adapter 在 Grok 硬擋 |
| 禁改 CC 系統 | `.grok/rules/00_cc_system_boundary.md` + 人審 |
| 雙跑防呆 | `compat.claude.hooks=false` |
| 開場不擋死 | SessionStart pull fail-open |
| 密鑰 | MCP／.env 不進腳本、不進 repo |
| Push（未來） | 標籤 + 目錄 + 掃 secret + CC 紅線 |

**已知限制：**  
Battle-tested 以 adapter 直調為主；TUI 14 handler 未逐支簽核。  
攔截文案仍可能寫「Anthropic」（CC 腳本原文）。

---

## 9. 失敗模式與排查

| 症狀 | 查 |
|------|-----|
| Grok 無硬閘 | `ls ~/.grok/hooks/cc-bridge-hooks.json`；config 是否 hooks=false 且檔被刪 |
| skill 沒了 | `ls -la ~/.claude/commands` 斷鏈；doctor |
| memory 舊 | 跑 `bridge_pull`；看 `_cc_bridge_meta.json` 時間 |
| Claude 變慢／記憶怪 | 是否誤 push 進 CC memory；查 `source: grok-build` |
| 雙重 hook | compat.hooks 是否又被改 true 且 bridge 仍在 |

```bash
python3 scripts/bridge_doctor.py
```

---

## 10. 與 Codex／其他 harness

見 `docs/04_harness_參數表.md`：複製本架構，填第三欄，改 adapter 與家目錄即可。  
**上下文隔離原則通用：** harness-specific → 該家目錄 rules；shared → CLAUDE／CC memory general。

---

## 11. 演進路線圖

| 階段 | 內容 | 狀態 |
|------|------|------|
| MVP | adapter + install + doctor | ✅ |
| 日用閉環 | memory pull、MCP 文檔、Battle-tested | ✅ |
| 隔離強化 | Grok-only rules、boundary rule | ✅ |
| 動態 pull | SessionStart bridge_pull | ✅ |
| **架構文檔** | 本檔 | ✅ |
| Memory 目錄三區 | `_from_cc` / `general` / `grok` | ⬜ 下一步 |
| Push general | `memory_push.py` + 目錄三區 | ✅ 2026-07-11 |
| Hook 煙測報告 | `docs/smoke_hooks_report.md` | ✅ |
| Hook 全套煙測 | doctor 擴充 | ⬜ |
| launchd 可選 | 模板不安裝 | ⬜ |

---

## 12. 詞彙表

| 詞 | 意思 |
|----|------|
| CC | Claude Code |
| Bridge | 本 repo + `~/.grok/hooks` 產物 |
| Adapter | `hook_adapter.py` |
| Pull | CC→Grok 更新 |
| Push | Grok→CC（受限、未默認） |
| Mirror | memory 檔案副本 |
| Grok-only | 只存在 `.grok` / `~/.grok`，不進 Claude 上下文 |
| SoT | Source of Truth 真相源 |
| Fail-open | 失敗不阻擋主流程（開場） |
| 煙測 | 見下節 |

---

## 13. 附：什麼是「煙測報告」？

**煙測（smoke test）**＝開工前抽幾條**最關鍵、最快**的檢查，確認「沒有整棟樓著火」，不是完整回歸測試。

**煙測報告**＝把這些檢查的：

- 指令  
- 通過／失敗  
- 一行輸出摘要  

寫成固定格式（例如塞進 `bridge_doctor` 或 `docs/smoke_report.md`）。

對本橋而言，煙測通常包括：

1. doctor 全綠  
2. 讀 `.env`／`.clasprc` 被 **deny**  
3. skill symlink 可讀  
4. memory 鏡像目錄存在  

**不是**「14 支 hook 每支在 TUI 真實打一遍」的完整 QA（那叫完整驗收）；煙測是完整驗收的子集。

---

## 14. 相關檔快速索引

| 問題 | 檔 |
|------|-----|
| 怎麼開 | `docs/01_絲滑啟動.md` |
| 差在哪 | `docs/00_差距矩陣.md` |
| Memory 操作 | `docs/02_memory.md` |
| MCP | `docs/03_mcp.md` |
| 換 Codex | `docs/04_harness_參數表.md` |
| 雙向階段 | `docs/05_dynamic_bidirectional_sync.md` |
| 本架構 | `architecture.md` |

標籤：#architecture #grok #claude-code #bridge
