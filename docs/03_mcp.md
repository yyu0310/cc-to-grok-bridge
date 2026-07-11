# 03_MCP — CC → Grok 遷移（四分類法）

> 上游：你自己的 MCP 清冊（只記名稱與型態，不記 secret）  
> **資安鐵則**：設定值（env / headers / token）**永不**進同步腳本、永不寫進本 repo 文檔。只記**名稱＋型態**。

## Grok MCP 放哪

- 使用者層：`~/.grok/config.toml` 的 `[mcp_servers.<name>]`
- 專案層：`<workspace>/.grok/config.toml`（可選）
- CLI：`grok mcp list` / `grok mcp add ...`（優先用 CLI，少手改含密 JSON）

```toml
# 範例形狀（值請自己填，不要從 CC 檔案抄進 git）
[mcp_servers.example_http]
url = "https://…"
headers = { Authorization = "Bearer …" }

[mcp_servers.example_stdio]
command = "npx"
args = ["-y", "some-mcp-server"]
# env = { API_KEY = "…" }   # 人填；腳本不碰
```

## 現況名稱清冊（2026-07-11，只名稱＋型態）

| 層 | Server | 型態 | Grok 遷移動作 |
|---|---|---|---|
| CC user（`~/.claude.json`） | `fireflies` | **API key / HTTP** | 人手：`grok mcp add --transport http …` 或 config 貼 **url 形狀**；**headers/key 由人從密碼管理器搬**，禁止腳本讀 CC json 的 headers |
| CC project（workspace） | `truenorth` | **HTTP（遠端 MCP）** | 同 fireflies：人手加 HTTP server；若需 auth 人填 headers |
| claude.ai 雲端 | Notion、Google Drive、TrueNorth、Blockscout | **claude.ai 雲端型** | **不可攜**。判定見下表 |
| claude.ai 雲端（待授權） | Google Calendar、Linear | 雲端 | 不可攜 |
| 專案 `.mcp.json` | （無） | — | 不用 |
| Lark | — | **本地 CLI 代理**（非 MCP） | **不搬 MCP**；Grok 直接用既有 `lark-*` skill + `lark-cli` |

## 四分類 × 動作

### 1. API key 型（fireflies/http）

- **做**：在 Grok 建同名或可辨識的 server；key **人搬**
- **不做**：任何從 `~/.claude.json` 複製 env/headers 的腳本
- **驗**：`grok mcp list` 看得到名稱；doctor 的 `check_mcp` 列得到 Grok 名稱（配置後）

### 2. OAuth 型（Gmail / Calendar / Drive 類原生 MCP）

- **做**：Grok 端各自走授權（瀏覽器 / device flow，依 server）
- **不做**：檔案同步 token
- **現況**：若使用者主力 Google 系只在 claude.ai connectors → 見第 3 類

### 3. claude.ai 雲端型（`mcp__claude_ai_*`）

綁 Claude 帳號，**不可攜**。逐一判定：

| Server | 判定 | Grok 建議 |
|---|---|---|
| Notion | 放棄 or 替代 | 找 Notion 官方/社群 MCP（stdio/http）人手裝；或維持 CC 做 Notion |
| Google Drive | 放棄 or 替代 | 官方 Google MCP / `gws` 類 CLI 若已有；否則 CC 專用 |
| TrueNorth（雲端 connector） | 與專案層 http 可能重疊 | 優先用 **專案層 truenorth HTTP** 遷到 Grok；雲端版放棄 |
| Blockscout | 放棄 or 替代 | 鏈上瀏覽改 WebFetch／專用 API；需要再裝 Blockscout MCP |
| Google Calendar / Linear | 待授權且雲端 | Grok 端另找 Calendar/Linear MCP 或保持 CC |

### 4. 本地 CLI 代理型（Lark）

- **只搬** command 使用方式（skill 已在 `~/.claude/commands` → Grok 已掃到）
- **token** 仍在既有 lark-cli 登入態，不經 MCP config

## 專案層 truenorth

| 項目 | 說明 |
|---|---|
| 型態 | HTTP 遠端 MCP（`type=http` + url） |
| 歸類 | 第 1 類變體（遠端 HTTP；auth 視 url/headers 是否需要） |
| 動作 | 人手加入 Grok `[mcp_servers.truenorth]`；**不**自動抄 url 進 repo（url 可出現在私人筆記，勿 commit secret） |
| 與雲端 TrueNorth | 並存於 CC；Grok 只遷 HTTP 這條較乾淨 |

## doctor

```bash
python3 scripts/bridge_doctor.py
# 章節「MCP」：列 CC 名稱＋型態、Grok 已配置名稱；未配置只 ℹ️ 不失敗
```

## 待人手（非腳本）

- [ ] 若日用要 fireflies：在 Grok 加 HTTP MCP（key 自備）
- [ ] 若日用要 truenorth：在 Grok 加 HTTP MCP
- [ ] Notion/Drive：決定替代 MCP 或留 CC

標籤：#mcp #grok #bridge
