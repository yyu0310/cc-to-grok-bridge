# 06_Plugins — Claude Code → Grok Build

> 相容等級：**低**（skill 清單可能看得見；**always-on 不會自動跟過去**）。  
> 用 plugin 的目的就是 **不用每場手動開**——遷移只談 always-on 路線。  
> 給 AI 的操作見 [AGENTS.md](../AGENTS.md)「Plugins」。

## 為什麼 CC 開了 plugin，Grok 卻「不行」

兩邊都叫 plugin，但**啟動機制不同**：

| | Claude Code | Grok Build |
|---|---|---|
| 登記 | `enabledPlugins`（settings）+ marketplace 安裝 | `grok plugin install` + `config.toml` 的 `[plugins].enabled`／`disabled` |
| 預設 | 啟用的 plugin 會掛上 | 文件：plugin **預設偏關**，要明確 enable／install 路徑 |
| Always-on | 常見：plugin **hooks**（如 SessionStart）每 session **自動注入**規則／模式 | 未裝 **Grok 版** plugin 時：**不會**跑 CC 的 plugin hooks |
| Skill 清單 | plugin 內 `skills/` | 可能掃得到 skill 名；**只有 always-on 路徑才算「裝了 plugin」** |
| Marketplace | Claude plugin marketplace | Grok 自己的 marketplace／git install；**不能**假設 `claude plugin install` 等價 |

實測常見落差（always-on 類 plugin）：

1. CC：`enabledPlugins` + SessionStart → **每場自動進入**該 plugin 模式  
2. Grok：若只「看得到」slash skill、沒裝 Grok plugin → **沒有** SessionStart 注入 → 體感沒載  
3. 上游 main 若只有 Claude 包裝、沒有 Grok adapter → **不能**對 main 跑 `grok plugin install` 就當完成

## 遷移策略（只保留 always-on）

### A. 原生 Grok plugin（真正的 plugin 路徑）

**是什麼：** 用 Grok 自己的 plugin 系統安裝一份**帶 Grok 包裝**的套件（hooks／marketplace 目錄對 Grok 有效），讓 SessionStart 等 lifecycle **自動跑**——效果對齊「CC 開了 auto plugin」。

**不是什麼：** 不是把 CC 的 `enabledPlugins` 勾選同步過去；也不是「skill 列表有名字」。

```bash
# 形狀（來源必須是「已含 Grok adapter」的 repo／ref）
grok plugin install <source> --trust   # hooks/MCP 通常要 --trust
grok plugin enable <name>              # 若 list 顯示 disabled
grok plugin list
grok plugin details <name>
```

- `~/.grok/config.toml` 可用 `[plugins] enabled = ["…"]` 強制開。  
- 裝完**重開 Grok session**。  
- **何時能對某插件走 A：** 上游已 merge Grok 支援，或你明確接受未 merge 的 fork／branch 並 `--trust`。  
- **何時還在等：** 官方 main 尚無 Grok 目錄／hooks 對應、PR 仍 open／conflict——這時 **A 對該插件尚未就緒**，改走 B，或等 merge 後再 A。

### B. Instruction 級 always-on（日用備援，仍免手動 slash）

把「每 session 都要遵守」的規則寫進：

- `<workspace>/.grok/rules/<name>.md`（開 workspace **自動載入**）

特點：

- **不用**每場打 slash——滿足「不要手動」  
- **不是**完整 plugin（常缺 mode 狀態機、statusline、每輪 hook 注入）  
- 不需 `--trust`；刪檔即回滾  
- 上游 A 就緒後應 **卸 B 或二選一**，避免雙載

## 橋接腳本現況

本 repo **尚未**提供「把 CC `enabledPlugins` 整包同步到 Grok」的腳本（且不應自動 `--trust`）。

日用：

1. `grok plugin list` — 空的但 CC 有啟用 → 預期落差  
2. 每個 always-on 能力：有 Grok 版 → **A**；否則 → **B**  
3. 公開文檔只寫型態；私人插件名留在你自己的筆記

## 驗收（always-on）

| 期望 | 怎麼驗 |
|------|--------|
| A 原生 plugin | `grok plugin list` enabled；`details` 有 hooks；**新 session 未 slash** 即表現出約束 |
| B rules | `.grok/rules/` 有檔；**新 session 未 slash** 即表現出約束 |

標籤：#plugins #grok #bridge
