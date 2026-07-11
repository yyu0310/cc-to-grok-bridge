# cc-to-grok-bridge

English | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

Bridge **Claude Code** → **Grok Build**: reuse rules / skills, run the same hook hard-gates via an adapter, optional memory mirror. Grok-only assets never enter Claude’s context.

## What this is

| Layer | What the bridge does |
|-------|----------------------|
| System Prompt | Point Grok at the same workspace `CLAUDE.md` (compat load) |
| skill | Reuse `~/.claude/commands` slash skills (including symlinks) |
| Hooks | Call your existing Claude Code security scripts through a thin adapter that translates allow/deny for Grok (see below) |
| Memory | CC → Grok pull + rules pointer + three-zone isolation; optional constrained push |
| Plugins | Does **not** auto-port CC `enabledPlugins`; always-on only — see [docs/06_plugins.md](docs/06_plugins.md) |
| MCP | AI-assisted install by **server type** (never auto-copy secrets; see AGENTS.md) |

## Compatibility matrix

| Domain | Compatibility | What works | Gaps |
|--------|---------------|------------|------|
| System Prompt | High | Same workspace CLAUDE.md (Grok compat auto-load) | — |
| skill | High | Same ~/.claude/commands set (symlinks OK) | Minor frontmatter / trigger differences |
| Hooks | Medium | Adapter + your CC hard-block scripts | Payload/deny translation; no full CC ask UI |
| Memory | High | memory_sync + rules pointer + three-zone layout; optional push | Not the same as CC MEMORY.md index load; product search optional |
| Plugins | Low | A: install when Grok packaging exists; B: rules always-on (see note) | CC settings do not auto-port; different marketplaces |
| MCP | Medium | Reinstall by type (HTTP key, OAuth, stdio); Notion/Google in docs | claude.ai cloud connectors not portable; secrets never auto-copied |

**In practice:** moving a Claude Code setup onto **Grok Build** is usually much smoother than the Antigravity / Gemini bridge path (real hard-blocks + simpler memory). Always-on plugins still need a deliberate path.

**Plugins note (Low = not drop-in, but documented fixes exist):**  
CC auto-enabled plugins ≠ Grok per-session injection. **A:** `grok plugin install` only when upstream has Grok packaging (SessionStart always-on). **B:** otherwise put always-on text in `.grok/rules/` (auto-load, no slash). See [docs/06_plugins.md](docs/06_plugins.md).  
**Outlook:** if most common plugins ship on the Grok marketplace with real Grok packaging, compatibility can rise to **medium–high** (still not auto-porting CC settings, but path A becomes normal and B is the exception).

Memory detail: bridge day-use does **not** require `[memory] enabled=true` first — the **rules pointer** loads with the project. Product memory improves search if you want it.

MCP detail: ask an AI coding agent to follow [AGENTS.md](AGENTS.md) (Notion, Google, OAuth). You approve the browser; you should not be asked to paste long terminal homework.

### What the hook adapter does (plain language)

Claude Code hooks are shell scripts (e.g. block reading `.env`). Grok also runs hooks, but the contracts differ:

1. **JSON field names on stdin differ** (payload shape)
2. **How “block this tool call” is reported differs** (deny protocol)

So you cannot point Grok straight at CC scripts. A thin **adapter** (`scripts/hook_adapter.py`) sits in the middle: Grok calls it; it calls your existing `~/.claude/hooks/*.sh`.

| Term | Meaning |
|------|---------|
| **Thin adapter** | Format translation only — does not reimplement the security policy |
| **Wraps CC scripts** | Invokes the same scripts; bodies stay on the CC side |
| **Payload normalize** | Map Grok field names to what CC scripts expect (e.g. `target_file` → `file_path`) |
| **Deny translate** | CC often uses `exit 2` + stderr; adapter emits Grok’s `{"decision":"deny", …}` |

Why this design:

- **Single source of truth** — blocklists stay in CC hooks
- **Hard block on Grok** — not “model please remember”; the tool call is actually denied
- **No forking CC scripts** — no need to edit `~/.claude/hooks/*.sh` just for Grok

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
| `docs/` | Gap matrix, day-to-day SOP, memory, MCP, plugins, harness table |

## Security

- Scripts never copy MCP env / tokens / OAuth secrets.
- Sensitive-read hard block is verified via adapter + your CC `block_sensitive_read` hook (e.g. `.clasprc*`, `.env`).
- Grok-only rules live under `<workspace>/.grok/rules/` and must not be written into Claude’s system files by this bridge.

## Limitations

1. MCP: secrets never auto-copied; claude.ai cloud connectors not portable — reinstall via [docs/03_mcp.md](docs/03_mcp.md) / [AGENTS.md](AGENTS.md)
2. Global Grok `~/.grok/memory/MEMORY.md` (`/remember`) ≠ CC project memory; sync uses a project subfolder
3. After install, restart the Grok session from the workspace root

## License

MIT — see [LICENSE](LICENSE).
