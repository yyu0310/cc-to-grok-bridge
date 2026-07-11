# 06_Plugins — Claude Code → Grok Build

> 相容等級：**中偏低**（skill 片段常看得見；**always-on plugin 行為不會自動跟過去**）。  
> 給 AI 的操作見 [AGENTS.md](../AGENTS.md)「Plugins」。

## 為什麼 CC 開了 plugin，Grok 卻「不行」

兩邊都叫 plugin，但**啟動機制不同**：

| | Claude Code | Grok Build |
|---|---|---|
| 登記 | `enabledPlugins`（settings）+ marketplace 安裝 | `grok plugin install` + `config.toml` 的 `[plugins].enabled`／`disabled` |
| 預設 | 啟用的 plugin 會掛上 | 文件：plugin **預設偏關**，要明確 enable／install 路徑 |
| Always-on | 常見：plugin **hooks**（如 SessionStart）每 session **自動注入**規則／模式 | 未裝 Grok 版 plugin 時：**不會**跑 CC 的 plugin hooks |
| Skill 清單 | plugin 內 `skills/` | 可能從掃描路徑「看得到」skill 名；**觸發才讀**，≠ always-on |
| Marketplace | Claude plugin marketplace | Grok 自己的 marketplace／git install；**不能**假設 `claude plugin install` 等價 |

實測常見落差（以「懶惰精簡」類 always-on plugin 為例，公開生態常見）：

1. CC：`enabledPlugins` + SessionStart → **每場自動進入精簡模式**  
2. Grok：slash skill 可能在列表裡，但 **沒有** 等同的 SessionStart 注入 → 體感「plugin 沒載」  
3. 官方 main 若只有 Claude plugin 結構、沒有 Grok adapter（例如缺 Grok 用的 plugin 目錄／hooks 對應）→ **不能**當成 Grok 原生 plugin 一鍵裝

## 遷移策略（由強到備援）

### A. 原生 Grok plugin（首選，若上游有）

```bash
# 形狀：git / GitHub shorthand / 本地 path；hooks+MCP 需 --trust
grok plugin install <source> --trust
grok plugin enable <name>    # 若 list 顯示 disabled
grok plugin list
grok plugin details <name>
```

- 在 `~/.grok/config.toml` 可用 `[plugins] enabled = ["…"]` 強制開。  
- 裝完**重開 Grok session**。  
- 上游 PR 未 merge／dirty 時：不要盲目 `--trust` fork；先讀 PR 與測試。

### B. Instruction 級 always-on（日用備援，bridge 友善）

把「每 session 都要遵守」的精簡規則寫進：

- `<workspace>/.grok/rules/<plugin-name>.md`，或  
- 使用者層 rules（若你的 Grok 版本支援）

特點：

- **開 workspace 就載**（與 `cc-memory-pointer` 同類）  
- **無**完整 plugin 狀態機（lite／full／ultra、statusline、每輪 hook 注入）  
- 不需 `--trust`；刪檔即回滾  
- 與之後正式 Grok plugin **二選一**，避免雙載

### C. 只當 skill 用

若你只需要 `/某指令` 偶爾跑：

- 確認 skill 在 Grok 掃得到的路徑（`~/.claude/commands` 或 plugin skills 掃描）  
- 手動 slash 觸發即可  
- **不要**期待「沒打指令也 always-on」

## 橋接腳本現況

本 repo **尚未**提供「把 CC `enabledPlugins` 整包同步到 Grok」的腳本（且不應自動 `--trust`）。

日用建議：

1. doctor 之後人工／AI 跑 `grok plugin list`  
2. 對每個 CC 啟用中的 plugin：查是否有 Grok 版 → A；否則 B 或 C  
3. 記錄在你自己的私人筆記；**公開文檔只寫型態，不強制具名私有插件**

## 驗收

| 期望 | 怎麼驗 |
|------|--------|
| Always-on 規則有生效 | 新 session 未 slash 就表現出該 plugin 的約束（或 rules 檔在 `.grok/rules/`） |
| 僅 skill | `/plugin-skill-name` 有內容；未觸發時不假設已注入 |
| 原生 plugin | `grok plugin list` 為 enabled；`details` 有 hooks／skills 清單 |

標籤：#plugins #grok #bridge
