# AI assistant notes — cc-to-grok-bridge

This repo is a **thin bridge**: Claude Code stays the source of truth for rules, skill bodies, and hook **scripts**. Grok Build is a guest that reuses them.

## Do

- Prefer existing scripts under `scripts/` over inventing parallel tooling.
- Keep defaults generic: workspace via `$CC_GROK_WORKSPACE` or `--workspace`, never hardcode a personal machine path.
- After install, remind the user to restart Grok from the **workspace root**.
- Treat MCP keys / OAuth as human-only; never copy secrets from `~/.claude.json` into this repo or into Grok config via scripts.

## Do not

- Modify `~/.claude/hooks/*.sh` bodies to “fix” Grok — use the adapter.
- Write Grok-only rules into `CLAUDE.md` or CC memory sources.
- Commit `.env`, real MCP tokens, or personal vault paths.
- Push to any company GitHub org; personal public repos only when the user asks.

## Verify（hook／adapter 改完必跑 — 全數，不是煙測）

改 `hook_adapter.py`、Grok-only gate、`install_bridge` 產物或任何會影響 deny／payload 的邏輯後，**必須**跑完整套，不可只跑 doctor 裡的單元煙測就當過：

```bash
export CC_GROK_WORKSPACE=~/path/to/your-workspace
# 若本機有 clasp sandbox 要驗真 push：
# export CC_GROK_CLASP_SANDBOX=~/path/to/clasp-run-sandbox

python3 scripts/bridge_doctor.py --workspace "$CC_GROK_WORKSPACE"
python3 scripts/hook_acceptance.py --with-clasp   # 全數；無 sandbox 時可先不加 --with-clasp 再補
```

判定：

- doctor：`fails=0`（全綠）
- acceptance：列印 `=== N/N PASS ===` 且 exit 0（含 adapter 單元、敏感讀、memory gate、lifecycle、可選真 clasp）

未過不准宣稱 DONE，不准 push。

## Key docs

- [architecture.md](architecture.md) — invariants
- [docs/01_絲滑啟動.md](docs/01_絲滑啟動.md) — daily SOP
- [docs/02_memory.md](docs/02_memory.md) — memory mirror
- [docs/03_mcp.md](docs/03_mcp.md) — MCP migration classes
