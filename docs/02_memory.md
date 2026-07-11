# 02_Memory — CC → Grok 單向同步

> 完整策略（general vs grok-specific、是否 push）見 [architecture.md §6](../architecture.md)。  
> **不變量：Grok-only 記憶／規則不進 Claude 開場上下文。**

## 機制（2026-07-11 落地）

| | Claude Code | Grok Build（橋接後） |
|---|---|---|
| 路徑 | `~/.claude/projects/<path-hash>/memory/` | `~/.grok/memory/<slug>-<sha256[:8]>/` |
| 開場載入 | MEMORY.md 前 200 行/25KB | 需 `[memory] enabled=true` 或 `--experimental-memory`；另有 rules 指標 |
| 真相來源 | **CC** | 鏡像；衝突時 **CC 蓋 Grok** |
| 同步 | — | `scripts/memory_sync.py`（手動，不掛排程） |

## 手動指令

```bash
cd /path/to/cc-to-grok-bridge

# 預覽（預設 workspace = $CC_GROK_WORKSPACE 或當前目錄）
python3 scripts/memory_sync.py --dry-run

# 執行
python3 scripts/memory_sync.py

# 自訂 workspace
python3 scripts/memory_sync.py --workspace ~/path/to/your-workspace
```

產物：

1. `~/.grok/memory/<slug>-<hash8>/*.md` — CC 同名檔覆寫
2. `~/.grok/memory/<slug>-<hash8>/_cc_bridge_meta.json` — 來源路徑與時間
3. `<workspace>/.grok/rules/cc-memory-pointer.md` — 短指標（Grok 必載 rules）

## 啟用 Grok memory（建議日用）

```toml
# ~/.grok/config.toml
[memory]
enabled = true
```

或單次：`grok --experimental-memory`

## 注意

- **不**把 CC 的 `MEMORY.md` 覆寫進 `~/.grok/memory/MEMORY.md`（那是 Grok **全域** remember 檔，2026-07-11 實測 `/remember` 寫在這）
- 不刪 Grok 端多出來的檔名（避免清掉原生筆記）
- 細節仍在 topic 檔；對話裡只跟指標走，勿整包貼 context
- 雙向同步刻意不做（漂移債）

## 與 AG bridge 差異

| AG `memory_sync.py` | 本橋 |
|---|---|
| CC ↔ AG KI 雙向 + prefix 防迴圈 | **僅 CC→Grok** |
| KI metadata.json + artifacts | 直接 md 鏡像 + meta json |

標籤：#grok #memory #bridge
