# 03_MCP — CC → Grok 遷移（型態分類 + 部署）

> **資安鐵則**：設定值（env / headers / token）**永不**進同步腳本、永不寫進本 repo。只記**型態＋做法**。  
> 給 AI 的逐步操作見根目錄 [AGENTS.md](../AGENTS.md)「MCP 部署手冊」。

## Grok MCP 放哪

- 使用者層：`~/.grok/config.toml` 的 `[mcp_servers.<name>]`
- 專案層：`<workspace>/.grok/config.toml`（可選；可分享形狀，**勿** commit 真 secret）
- CLI：`grok mcp list` / `grok mcp add …` / `grok mcp doctor`（優先用 CLI）

```toml
# 形狀範例（值請自己填，不要從 CC 設定檔抄進 git）
[mcp_servers.example_http]
url = "https://…"
headers = { Authorization = "Bearer …" }

[mcp_servers.example_stdio]
command = "npx"
args = ["-y", "some-mcp-server"]
# env = { API_KEY = "…" }   # 人授權後由 AI 寫入本地 config；勿貼進公開 repo
```

## 四分類（用特質，不用具體私有服務名）

| 型態 | 特徵 | 可否自動從 CC 搬 | Grok 做法 |
|------|------|------------------|-----------|
| **A. API key / Bearer HTTP** | 遠端 URL + header 或 env 裡一串 key | **否**（禁止腳本讀 CC 的 secret） | 人從密碼管理器取出 key → **AI 代跑** `grok mcp add --transport http …` 或寫 user-scope config |
| **B. 遠端 HTTP（可選 auth）** | 有 URL；auth 可有可無 | **否**（URL／header 勿進 git） | 同上；doctor 只驗名稱是否出現 |
| **C. OAuth／瀏覽器授權** | 需登入 Google／Notion 等帳號 | **否**（登入態不可檔案複製） | **由 AI 啟動授權流程**（CLI／官方 MCP 的 login）；**不要**叫用戶手貼一長串指令到 terminal |
| **D. claude.ai 雲端 connector** | 只存在 Claude 帳號雲端、工具名常帶雲端前綴 | **不可攜** | 放棄雲端那條；在 Grok 改裝 **獨立** stdio／HTTP MCP（見下） |
| **E. 本地 CLI 代理** | 其實不是 MCP，是本機 CLI + skill | 不必搬 MCP | skill 已在 `~/.claude/commands` 時 Grok 可掃到；登入態留在該 CLI |

## 日用優先：Notion、Google

這兩類最常卡在「CC 雲端有、Grok 沒有」。正確路徑是 **D → C/A**：不要幻想搬 claude.ai connector，改裝獨立 MCP。

### Notion

1. 判定：若只在 claude.ai connectors → **不可攜**，改走獨立 MCP。  
2. 選一個社群／官方 **stdio 或 HTTP** Notion MCP（依你當下生態選高星、文件清楚的）。  
3. **請 AI 執行**（不要自己手貼）：
   - 確認 Node／npx 可用
   - `grok mcp add …`（stdio）或 HTTP + token
   - Notion integration token 從 Notion 開發者後台建立；**只放本機** env 或 user config，不進 git  
4. 驗：`grok mcp list` 看得到名稱；`grok mcp doctor <name>`；開新 Grok session 試讀一頁。

### Google（Drive／Gmail／Calendar 等）

1. 判定：claude.ai 上的 Google connector → **不可攜**。  
2. 優先選 **會走 OAuth／device flow 的官方或社群 Google MCP**（不要用「把 refresh token 貼進 README」這種教學）。  
3. **請 AI 執行授權**：
   - AI 跑 add／login 指令
   - 瀏覽器跳出時**你只負責點允許**
   - 禁止：「請把下面整段 export 貼到 terminal」當唯一路徑  
4. 若某 Google 能力只有 API key 型 server：走型態 A，key 從 GCP 控制台建，AI 寫入 user-scope，不 commit。  
5. 驗：同 Notion；並確認重開 session 後工具仍在。

### 其他常見型態（摘要）

| 需求 | 建議 |
|------|------|
| 遠端 HTTP API（會議／CRM／內網工具） | 型態 A/B：URL + header；key 人授、AI 裝 |
| 議題追蹤（Linear 類） | 多為 HTTP/SSE；同 A/B |
| 鏈上瀏覽 | 可選專用 MCP 或先用 WebFetch |
| 即時通訊本地 CLI | 型態 E：skill + CLI 登入，不強行 MCP 化 |

## 給 AI 的硬規則（部署時）

1. **禁止**讀取／複製 `~/.claude.json` 或任何 CC 設定裡的 env／headers 實值。  
2. **禁止**把 key 寫進本 bridge repo 或專案層會被 commit 的檔。  
3. OAuth：**AI 跑指令 + 用戶只點瀏覽器同意**；不要把「用戶手貼 terminal」當預設。  
4. 裝完跑 `grok mcp list` 與 `grok mcp doctor`；失敗先看 timeout（冷啟動 npx 可加長 `startup_timeout_sec`）。  
5. doctor 的 bridge `check_mcp`：未配置只 ℹ️，**不算** bridge 安裝失敗。

## doctor

```bash
python3 scripts/bridge_doctor.py --workspace ~/path/to/your-workspace
# 章節「MCP」：列 CC 側名稱＋型態摘要、Grok 已配置名稱；未配置不失敗
```

標籤：#mcp #grok #bridge
