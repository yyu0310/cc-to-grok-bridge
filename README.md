# cc-to-grok-bridge

English | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

Bridge **Claude Code** → **Grok Build**: reuse rules / skills, run the same hook hard-gates via an adapter, optional memory mirror. Grok-only assets never enter Claude’s context.

## What this is

| Layer | What the bridge does |
|-------|----------------------|
| Rules / skills | Point Grok at the same `CLAUDE.md` + `~/.claude/commands` you already use |
| Hooks | Wrap CC hook scripts with a thin adapter (payload + deny protocol) |
| Memory | Optional one-way mirror: CC → Grok (`_from_cc` / `general` / `grok` isolation) |
| MCP | Docs only — never auto-copy API keys or OAuth tokens |

## Requirements

- macOS or Linux with Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) already set up (hooks under `~/.claude/hooks/`, skills under `~/.claude/commands/`)
- [Grok Build](https://x.ai/) CLI / TUI
- No API key required for the bridge scripts themselves

## Quick start

```bash
git clone https://github.com/<YOUR_USERNAME>/cc-to-grok-bridge.git
cd cc-to-grok-bridge

# From your real workspace root (the folder that has CLAUDE.md / .grok/)
export CC_GROK_WORKSPACE=~/path/to/your-workspace

python3 scripts/install_bridge.py
python3 scripts/memory_sync.py --workspace "$CC_GROK_WORKSPACE"
python3 scripts/bridge_doctor.py --workspace "$CC_GROK_WORKSPACE"   # expect fails=0
```

Then open Grok from that workspace and restart the session so hooks reload.

## Layout

| Path | Role |
|------|------|
| `scripts/hook_adapter.py` | Normalize Grok payload → CC hook stdin; translate deny |
| `scripts/install_bridge.py` | Install adapter + Grok hooks JSON; disable double-fire |
| `scripts/memory_sync.py` | CC → Grok memory pull |
| `scripts/memory_push.py` | Optional constrained push: `general/` → CC |
| `scripts/bridge_doctor.py` | Read-only health check + hard-block smoke |
| `scripts/hook_acceptance.py` | Adapter-layer acceptance tests |
| `architecture.md` | Design invariants (source of truth for “why”) |
| `docs/` | Gap matrix, day-to-day SOP, memory, MCP, harness table |

## Security

- Scripts never copy MCP env / tokens / OAuth secrets.
- Sensitive-read hard block is verified via adapter + your CC `block_sensitive_read` hook (e.g. `.clasprc*`, `.env`).
- Grok-only rules live under `<workspace>/.grok/rules/` and must not be written into Claude’s system files by this bridge.

## Limitations

1. MCP keys / OAuth: human-only; see `docs/03_mcp.md`
2. claude.ai cloud connectors are not portable
3. Product Grok memory (`~/.grok/memory/MEMORY.md`) is not the same as CC project memory; sync writes a project subfolder
4. After install, restart the Grok session from the workspace root

## License

MIT — see [LICENSE](LICENSE).
