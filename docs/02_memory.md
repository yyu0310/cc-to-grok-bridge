# 02_Memory — CC → Grok（日用好處理）

> 完整策略（general vs grok-specific、是否 push）見 [architecture.md §6](../architecture.md)。  
> **不變量：Grok-only 記憶／規則不進 Claude 開場上下文。**

## 機制（實測日用）

| | Claude Code | Grok Build（橋接後） |
|---|---|---|
| 路徑 | `~/.claude/projects/<path-hash>/memory/` | `~/.grok/memory/<slug>-<sha256[:8]>/`（三區：`_from_cc`／`general`／`grok`） |
| 開場怎麼「有記憶」 | 載 `MEMORY.md` 索引前段 | **主線：rules 指標** `cc-memory-pointer.md`（Grok 開 workspace 就會載 `.grok/rules/`）+ 磁碟上的鏡像檔；**不必**為了 bridge 先開產品 memory 開關 |
| 產品 memory 搜尋 | — | 可選加強（`memory_search` 等）。官方文件預設實驗功能可關；**已開或 session 內 `/memory on` 會更好搜，但不是 bridge 硬前置** |
| 真相來源 | **CC** | 鏡像；衝突時 **CC 蓋 `_from_cc` 同名檔** |
| 同步 | — | `scripts/memory_sync.py`（pull）；SessionStart 可掛 `bridge_pull`；`memory_push.py` 可選把 `general/` 寫回 CC |

## 為什麼說 memory「好處理」

1. **一條指令 pull**：`memory_sync.py --workspace …`  
2. **硬隔離三區**：手寫不進 `_from_cc`；Grok-only 進 `grok/`；跨 harness 事實進 `general/`  
3. **短指標進 rules**：不用把整包 memory 塞進 Claude  
4. **可選 push**：有 secret 掃描 + MEMORY.md 紅線，不會默默灌爆 CC  
5. 比 Antigravity 路線單純：不必維護另一套 KI metadata／雙向 prefix 防迴圈也能日用

## 手動指令

```bash
cd /path/to/cc-to-grok-bridge

# 預覽（預設 workspace = $CC_GROK_WORKSPACE 或當前目錄）
python3 scripts/memory_sync.py --dry-run

# 執行
python3 scripts/memory_sync.py --workspace ~/path/to/your-workspace

# 可選：把 general/ 受限推回 CC
python3 scripts/memory_push.py --workspace ~/path/to/your-workspace --dry-run
```

產物：

1. `~/.grok/memory/<slug>-<hash8>/_from_cc/*.md` — CC 鏡像（pull 可覆蓋）  
2. 同層 `general/`、`grok/` — 寫入分工  
3. `_cc_bridge_meta.json` — 來源與時間  
4. `<workspace>/.grok/rules/cc-memory-pointer.md` — 短指標（**開場就載**）

## 產品 memory 開關（可選，不是 bridge 門檻）

若你要完整產品側搜尋／注入，可擇一：

- session：`/memory on`  
- 或 config：`[memory] enabled = true`  
- 或 `GROK_MEMORY=1` / `grok --experimental-memory`  

關閉：`grok --no-memory`（最高優先）。  
**bridge 的 pull／pointer／三區不依賴你一定開這個。**

## 注意

- **不**把 CC 的 `MEMORY.md` 覆寫進 `~/.grok/memory/MEMORY.md`（那是 Grok **全域** `/remember` 檔）  
- 不刪 Grok 端多出來的檔名（避免清掉原生筆記）  
- 細節仍在 topic 檔；對話跟指標走，勿整包貼 context  

## 與 AG bridge 差異

| AG `memory_sync` 路線 | 本橋 |
|---|---|
| 常要雙向 + prefix 防迴圈、KI 結構 | **日用單向 CC→Grok 即可**；push 明示才做 |
| 另一套 IDE 載入語意 | Grok 原生吃 rules + 可選產品 memory，體感更貼 CC |

標籤：#grok #memory #bridge
