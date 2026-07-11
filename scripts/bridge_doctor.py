#!/usr/bin/env python3
"""
bridge_doctor.py — 檢查 CC→Grok 橋接是否就緒（唯讀，不讀 secret 值）。

用法：
  python3 bridge_doctor.py
  python3 bridge_doctor.py --workspace ~/path/to/your-workspace
  python3 bridge_doctor.py --strict   # frontmatter 缺漏也算失敗
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


HOME = Path.home()
FAILS = 0
WARNS = 0


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def info(msg: str) -> None:
    print(f"  ℹ️  {msg}")


def warn(msg: str) -> None:
    global WARNS
    WARNS += 1
    print(f"  ⚠️  {msg}")


def bad(msg: str) -> None:
    global FAILS
    FAILS += 1
    print(f"  ❌ {msg}")


def section(title: str) -> None:
    print(f"\n## {title}")


def check_workspace(ws: Path) -> None:
    section("工作區")
    if not ws.is_dir():
        bad(f"工作區不存在: {ws}")
        return
    ok(f"工作區: {ws}")
    claude = ws / "CLAUDE.md"
    if claude.is_file():
        ok(f"CLAUDE.md 存在 ({claude.stat().st_size} bytes) — Grok 會自動載入")
    else:
        bad("缺少 CLAUDE.md")
    rules = ws / ".grok" / "rules"
    if rules.is_dir():
        mds = list(rules.glob("*.md"))
        ok(f".grok/rules/ 有 {len(mds)} 個 md: {[p.name for p in mds]}")
    else:
        warn("尚無 .grok/rules/")


def check_skills(strict: bool) -> None:
    section("Skills（~/.claude/commands）")
    cmd = HOME / ".claude" / "commands"
    if not cmd.is_dir():
        bad(f"找不到 {cmd}")
        return
    files = sorted(cmd.glob("*.md"))
    ok(f"commands 數量: {len(files)}")
    no_fm = []
    for p in files:
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not t.startswith("---"):
            no_fm.append(p.name)
    if no_fm:
        msg = f"{len(no_fm)} 個缺 YAML frontmatter: {no_fm[:8]}"
        if strict:
            bad(msg)
        else:
            info(msg + "（可接受：slash 仍可用；--strict 才當失敗）")
    else:
        ok("全部有 frontmatter")
    broken = [p.name for p in files if p.is_symlink() and not p.exists()]
    if broken:
        bad(f"斷裂 symlink: {broken}")
    else:
        ok("symlink 無斷鏈")

    # skill 內容可讀煙測（ref-audit）
    ref = cmd / "ref-audit.md"
    if ref.is_file() or ref.is_symlink():
        try:
            text = ref.read_text(encoding="utf-8", errors="replace")
            if "name: ref-audit" in text or text.startswith("---"):
                ok(f"skill 內容可讀: ref-audit.md ({len(text)} bytes via symlink)")
            else:
                warn("ref-audit.md 可讀但格式異常")
        except OSError as e:
            bad(f"無法讀 ref-audit.md: {e}")
    else:
        warn("無 ref-audit.md（改抽樣其他 skill）")


def check_hooks() -> None:
    section("Hooks")
    settings = HOME / ".claude" / "settings.json"
    if settings.is_file():
        data = json.loads(settings.read_text(encoding="utf-8"))
        events = list((data.get("hooks") or {}).keys())
        ok(f"CC settings.json hooks events: {events}")
    else:
        bad("無 ~/.claude/settings.json")

    hooks_dir = HOME / ".claude" / "hooks"
    if hooks_dir.is_dir():
        sh = list(hooks_dir.glob("*.sh"))
        ok(f"CC hook 腳本: {len(sh)} 支")
        for s in sh:
            if not os.access(s, os.X_OK):
                warn(f"不可執行: {s.name}")
    else:
        warn("無 ~/.claude/hooks/")

    grok_hooks = HOME / ".grok" / "hooks"
    bridge = grok_hooks / "cc-bridge-hooks.json"
    adapter = grok_hooks / "_cc_bridge_adapter.py"
    if bridge.is_file():
        ok(f"已安裝 bridge hooks: {bridge}")
        try:
            j = json.loads(bridge.read_text(encoding="utf-8"))
            ok(f"  events: {list((j.get('hooks') or {}).keys())}")
        except json.JSONDecodeError as e:
            bad(f"bridge json 損壞: {e}")
    else:
        bad("尚未 install_bridge.py → 缺少 ~/.grok/hooks/cc-bridge-hooks.json")

    if adapter.exists():
        ok(f"adapter: {adapter}")
    else:
        bad("缺少 adapter ~/.grok/hooks/_cc_bridge_adapter.py")

    cfg = HOME / ".grok" / "config.toml"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8")
        if re.search(r"(?ms)\[compat\.claude\].*?hooks\s*=\s*false", text):
            ok("config.toml: [compat.claude] hooks = false（避免雙跑）")
        else:
            warn("config.toml 未設 hooks=false — 可能雙重觸發")
    else:
        warn("無 ~/.grok/config.toml")


def check_memory(ws: Path) -> None:
    section("Memory")
    cc_hash = str(ws.resolve()).replace("/", "-").replace(" ", "-")
    cc_mem = HOME / ".claude" / "projects" / cc_hash / "memory" / "MEMORY.md"
    if cc_mem.is_file():
        ok(f"CC MEMORY.md: {cc_mem} ({cc_mem.stat().st_size} bytes)")
    else:
        bad(f"CC MEMORY.md 不存在: {cc_mem}")

    # bridge target via meta scan
    base = HOME / ".grok" / "memory"
    target = None
    if base.is_dir():
        for d in base.iterdir():
            if not d.is_dir():
                continue
            meta = d / "_cc_bridge_meta.json"
            if meta.is_file():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    if data.get("workspace") == str(ws.resolve()):
                        target = d
                        break
                except (json.JSONDecodeError, OSError):
                    pass
    if target and (target / "_cc_bridge_meta.json").is_file():
        from_cc = target / "_from_cc"
        mem = from_cc / "MEMORY.md" if from_cc.is_dir() else target / "MEMORY.md"
        if mem.is_file():
            ok(f"Grok memory root: {target}")
            ok(f"  _from_cc mirror: {mem} ({mem.stat().st_size} bytes)")
        else:
            warn(f"meta 在但缺 MEMORY.md 鏡像: {from_cc}")
        for sub in ("_from_cc", "general", "grok"):
            p = target / sub
            if p.is_dir():
                ok(f"  layout {sub}/ ({len(list(p.glob('*.md')))} md)")
            else:
                warn(f"  缺 layout {sub}/")
        ok(f"  meta: {target / '_cc_bridge_meta.json'}")
    else:
        bad("尚未 memory_sync → 缺 ~/.grok/memory/*/_cc_bridge_meta.json 對應本 workspace")

    pointer = ws / ".grok" / "rules" / "cc-memory-pointer.md"
    if pointer.is_file():
        ok(f"rules pointer: {pointer.name}")
    else:
        warn("缺 .grok/rules/cc-memory-pointer.md（跑 memory_sync 會寫）")

    cfg = HOME / ".grok" / "config.toml"
    mem_on = False
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8")
        mem_on = bool(re.search(r"(?ms)\[memory\].*?enabled\s*=\s*true", text))
    if mem_on:
        ok("Grok [memory] enabled = true")
    else:
        info("Grok memory 未在 config 啟用（可用 --experimental-memory；指標仍靠 rules pointer）")


def _mcp_names_from_claude_json() -> dict:
    """只回名稱與型態，永不回傳 env/headers 值。"""
    p = HOME / ".claude.json"
    out = {"user": {}, "projects": {}}
    if not p.is_file():
        return out
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return out

    def classify(cfg: dict) -> str:
        if not isinstance(cfg, dict):
            return "unknown"
        if cfg.get("type") == "http" or "url" in cfg:
            return "http"
        if "command" in cfg:
            return "stdio"
        return str(cfg.get("type") or "unknown")

    for name, cfg in (data.get("mcpServers") or {}).items():
        out["user"][name] = classify(cfg if isinstance(cfg, dict) else {})

    for path, cfg in (data.get("projects") or {}).items():
        if not isinstance(cfg, dict):
            continue
        ms = cfg.get("mcpServers") or {}
        if ms:
            out["projects"][path] = {n: classify(c if isinstance(c, dict) else {}) for n, c in ms.items()}
    return out


def _mcp_names_from_grok() -> list[str]:
    names: list[str] = []
    for cfg_path in (HOME / ".grok" / "config.toml",):
        if not cfg_path.is_file():
            continue
        text = cfg_path.read_text(encoding="utf-8")
        names.extend(re.findall(r"(?m)^\[mcp_servers\.([^\]]+)\]", text))
    # project-level
    # also scan common workspace default later by caller
    return names


def check_mcp(ws: Path) -> None:
    section("MCP（只查名稱，不讀 secret）")
    cc = _mcp_names_from_claude_json()
    if cc["user"]:
        ok(f"CC user MCP: {sorted(cc['user'].items())}")
    else:
        info("CC user 層無 mcpServers")

    proj_hit = False
    for path, servers in cc["projects"].items():
        if path == str(ws) or path.rstrip("/") == str(ws).rstrip("/") or ws.name in path:
            ok(f"CC project MCP ({path}): {sorted(servers.items())}")
            proj_hit = True
    if not proj_hit:
        info("CC 本 workspace 專案層無 mcpServers 或 path 未匹配")

    grok_names = _mcp_names_from_grok()
    proj_cfg = ws / ".grok" / "config.toml"
    if proj_cfg.is_file():
        text = proj_cfg.read_text(encoding="utf-8")
        grok_names.extend(re.findall(r"(?m)^\[mcp_servers\.([^\]]+)\]", text))
    grok_names = sorted(set(grok_names))

    if grok_names:
        ok(f"Grok mcp_servers 名稱: {grok_names}")
    else:
        # 依 mcp 管理：key 由人搬，未配置是預期初始態
        info(
            "Grok 尚無 [mcp_servers.*]（API key/OAuth 需人手；見 docs/03_mcp.md）。"
            "不算 bridge 安裝失敗。"
        )

    # inventory expected portable types
    info("claude.ai 雲端 connectors 不可攜 — doctor 不列為失敗")
    info("Lark 走 lark-cli skill，非 MCP — 不需 mcp_servers")


def check_adapter_unit() -> None:
    section("Adapter 單元煙測（含 clasprc / .env）")
    adapter = HOME / ".grok" / "hooks" / "_cc_bridge_adapter.py"
    repo_adapter = Path(__file__).resolve().parent / "hook_adapter.py"
    script = adapter if adapter.exists() else repo_adapter
    real_hook = HOME / ".claude" / "hooks" / "block_sensitive_read.sh"

    if not script.is_file():
        bad("找不到 hook_adapter.py")
        return

    def run_payload(payload: dict) -> tuple[int, str, str]:
        hook = str(real_hook) if real_hook.is_file() else None
        if hook is None:
            # fallback fake hook
            fake = """#!/bin/bash
INPUT=$(cat)
PATHF=$(echo "$INPUT" | /usr/bin/jq -r '.tool_input.file_path // empty')
if [[ "$PATHF" == *".env"* ]] || [[ "$PATHF" == *".clasprc"* ]]; then
  echo "blocked" >&2
  exit 2
fi
exit 0
"""
            with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
                f.write(fake)
                hook = f.name
            os.chmod(hook, 0o755)
            cleanup = hook
        else:
            cleanup = None
        try:
            proc = subprocess.run(
                [sys.executable, str(script), hook],
                input=json.dumps(payload).encode(),
                capture_output=True,
            )
            return proc.returncode, proc.stdout.decode(), proc.stderr.decode()
        finally:
            if cleanup:
                os.unlink(cleanup)

    # clasprc
    code, out, err = run_payload(
        {
            "toolName": "read_file",
            "toolInput": {"target_file": str(HOME / ".clasprc.json")},
        }
    )
    if code == 2 and "deny" in out:
        ok(f"硬擋 ~/.clasprc.json PASS (exit=2, reason 含 deny)")
        info(f"  stdout摘要: {out.strip()[:160]}")
    else:
        bad(f"硬擋 clasprc FAIL code={code} out={out[:200]!r}")

    # .env
    code2, out2, _ = run_payload(
        {
            "toolName": "read_file",
            "toolInput": {"target_file": str(Path("/tmp/demo/.env"))},
        }
    )
    if code2 == 2 and "deny" in out2:
        ok("硬擋 .env PASS")
    else:
        bad(f"硬擋 .env FAIL code={code2}")

    # allow
    code3, out3, _ = run_payload(
        {
            "toolName": "read_file",
            "toolInput": {"target_file": str(Path.cwd() / "README.md")},
        }
    )
    if code3 == 0 and "allow" in out3:
        ok("放行一般檔案 PASS")
    else:
        bad(f"放行 FAIL code={code3} out={out3[:200]!r}")


def main() -> int:
    global FAILS, WARNS
    FAILS = 0
    WARNS = 0

    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(Path(os.environ.get("CC_GROK_WORKSPACE", str(Path.cwd()))).expanduser()))
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    ws = Path(os.path.expanduser(args.workspace)).resolve()

    print("# cc-to-grok-bridge doctor")
    print(f"workspace={ws}")

    check_workspace(ws)
    check_skills(args.strict)
    check_hooks()
    check_memory(ws)
    check_mcp(ws)
    check_adapter_unit()

    section("總結")
    if FAILS == 0:
        ok(f"全綠（fails=0, warns={WARNS}）")
        print("\n日用：cd workspace && grok")
        print("memory 更新：python3 scripts/memory_sync.py")
        print("MCP 手搬：見 docs/03_mcp.md")
        return 0
    bad(f"fails={FAILS}, warns={WARNS}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
