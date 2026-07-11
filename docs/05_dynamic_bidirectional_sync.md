# 05_動態雙向同步 — 設計與分階段

> 狀態：設計 + 第一階段掛點（SessionStart 拉 memory）  
> 原則：CC 系統檔預設只讀；任何寫回 CC 必須白名單 + 明確策略。

## 0. 靜態 vs 動態

| | 靜態 | 動態（現行首選） |
|---|---|---|
| 觸發 | 人手跑 `install_bridge` / `memory_sync` | **SessionStart → bridge_pull**（fail-open）；必要時手動 pull |
| memory | 僅手動 mirror | 開場自動 pull（CC→Grok） |
| hooks 包裝 | 僅手動 install | CC settings.json mtime 較新 → 開場重包 |
| skills | **活 symlink**（改正文即生效） | 不進 pull；doctor 斷鏈即可 |
| 寫回 CC | 無默認 | 僅白名單 + 用戶明示（見 §3） |
| launchd | — | **預設不安裝**（見下方決策） |

### 決策：為何不用 launchd 當預設（2026-07-12 · 給其他 harness 橋沿用）

- 用 harness 時才需要最新 CC 狀態 → **開 session 拉一次**語意正確。  
- 不定時背景跑：省電、少 plist 故障面、失敗用 fail-open 不擋開場。  
- 新 CC hook：寫進 settings → 下次 SessionStart stale install 即可；只改腳本正文則 adapter 已直調本體。  
- launchd 僅當「長期不開該 CLI 也要更新鏡像」才當**可選加菜**，勿當母版預設。

## 1. 各域「誰是真相源」

| 域 | Source of truth | Grok 可寫？ | 雙向？ |
|---|---|---|---|
| CLAUDE.md | CC／vault 根 | **禁止**（見 00_cc_system_boundary） | 否 |
| `.grok/rules/*` | Grok | 是 | 否（不回寫 CC） |
| hooks 腳本 `~/.claude/hooks` | CC | 禁止改腳本 | 否；只重包 JSON |
| hooks 註冊 settings | CC | 禁止改 | Grok 側 JSON 由 install 重生 |
| skills 正文 SKILL/ | vault | 經 symlink 已共享 | 實時＝已雙端同檔 |
| memory | **CC** `…/memory/` | 鏡像目錄可寫但會被 pull 覆蓋 | 預設 **單向 pull**；push 需明示 |
| MCP secrets | 人 | 禁止腳本搬 key | 否 |
| MCP **名稱清單** | 盤點文檔 | 可更新 bridge 文檔 | 文檔級 |

## 2. 建議管線（自動化）

```
[SessionStart on Grok]
    → bridge_pull.sh
         1) memory_sync.py          # CC → Grok 鏡像
         2) install_bridge.py --if-stale   # settings/hooks mtime 變才重包
         3) bridge_doctor.py --quiet       # 失敗只警告不擋開場

[不要預設 launchd]
    → 非「用才同步」需求勿裝

[明確用戶指令「push memory to CC」]
    → memory_push.py   # 僅 topic 白名單；永不默認
```

## 3. 雙向 memory 的危險與白名單（未實作 push 前）

- CC MEMORY.md 有 145 行／22.5KB 紅線與 write_gate  
- Grok `/remember` 寫 **全域** `~/.grok/memory/MEMORY.md`，與專案鏡像不同  
- **禁止** 把 Grok 全域 MEMORY 整包灌進 CC  
- 未來 push 若做：只允許 `feedback_*.md` / 用戶點名檔；先 diff 再寫；走 ask

## 4. 第一階段落地（本迭代）

1. `scripts/bridge_pull.py` — 串 memory_sync + 可選 stale install  
2. Grok `SessionStart` hook → 呼叫 bridge_pull（fail-open）  
3. `install_bridge.py --if-stale` — 比對 CC settings mtime vs bridge json  

## 5. 第二階段（下一步）

- skills 斷鏈自動修（只重建 `~/.claude/commands` symlink？**碰 CC** → 需用戶開閘；或只報警）  
- MCP 名稱 diff 報告（永不抄 secret）  
- launchd：**不排進預設**；有明確「不開 harness 也要鏡像」需求再當可選模板

## 6. 第三階段（真·雙向）

- 策略檔 `sync_policy.toml`：path 級 read/write  
- 審計 log：`~/.grok/bridge-audit/*.jsonl`  
- 一律可 `--dry-run`

標籤：#bridge #sync
