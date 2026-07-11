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

## Verify

```bash
python3 scripts/bridge_doctor.py --workspace ~/path/to/your-workspace
python3 scripts/hook_acceptance.py
```

Expect doctor `fails=0` when the user’s CC hooks and Grok install are healthy.

## Key docs

- [architecture.md](architecture.md) — invariants
- [docs/01_絲滑啟動.md](docs/01_絲滑啟動.md) — daily SOP
- [docs/02_memory.md](docs/02_memory.md) — memory mirror
- [docs/03_mcp.md](docs/03_mcp.md) — MCP migration classes
