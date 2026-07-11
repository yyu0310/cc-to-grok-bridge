#!/usr/bin/env python3
"""
install_bridge.py — 把 CC hooks 包一層 adapter 掛進 ~/.grok/hooks/，
並建議（可寫入）關閉 Grok 對 ~/.claude/settings.json 的 hooks 掃描，避免雙重觸發。

預設：
  - 讀 ~/.claude/settings.json 的 hooks
  - 寫 ~/.grok/hooks/cc-bridge-hooks.json
  - 寫 ~/.grok/hooks/_cc_bridge_adapter.py（本 repo 腳本的副本或 symlink）
  - 更新 ~/.grok/config.toml：[compat.claude] hooks = false

用法：
  python3 install_bridge.py              # 執行安裝
  python3 install_bridge.py --dry-run    # 只印將做的事
  python3 install_bridge.py --keep-claude-hooks  # 不關 compat hooks（可能雙跑）
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


HOME = Path.home()
CLAUDE_SETTINGS = HOME / ".claude" / "settings.json"
GROK_HOOKS_DIR = HOME / ".grok" / "hooks"
GROK_CONFIG = HOME / ".grok" / "config.toml"
OUT_HOOKS_JSON = GROK_HOOKS_DIR / "cc-bridge-hooks.json"
ADAPTER_NAME = "_cc_bridge_adapter.py"

# 這個腳本所在 repo
REPO_SCRIPTS = Path(__file__).resolve().parent
REPO_ADAPTER = REPO_SCRIPTS / "hook_adapter.py"


def load_claude_hooks() -> dict:
    if not CLAUDE_SETTINGS.is_file():
        raise SystemExit(f"找不到 {CLAUDE_SETTINGS}")
    data = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    hooks = data.get("hooks")
    if not hooks:
        raise SystemExit("settings.json 沒有 hooks 段")
    return hooks


def wrap_command(command: str, adapter: Path) -> str:
    """
    把 CC 的 command 包成：python3 adapter <original>
    支援：
      /abs/path/script.sh
      /abs/path/script.sh --flag
    內嵌 shell one-liner 則：python3 adapter -- bash -lc '...'
    """
    command = command.strip()
    # 已是 adapter 包過的不重複包
    if "_cc_bridge_adapter.py" in command or "hook_adapter.py" in command:
        return command

    # 絕對路徑腳本（可含參數）
    m = re.match(r"^(/\S+\.(?:sh|py|bash))(\s+.*)?$", command)
    if m:
        script = m.group(1)
        rest = (m.group(2) or "").strip()
        parts = [sys.executable, str(adapter), script]
        if rest:
            # 剩餘參數原樣附加（簡易）
            return " ".join(parts) + " " + rest
        return " ".join(parts)

    # 其他：用 bash -lc 包
    # 注意：引號逃逸
    escaped = command.replace("'", "'\"'\"'")
    return f"{sys.executable} {adapter} /bin/bash -lc '{escaped}'"


def transform_hooks(hooks: dict, adapter: Path) -> dict:
    out: dict = {}
    for event, matchers in hooks.items():
        if not isinstance(matchers, list):
            out[event] = matchers
            continue
        new_matchers = []
        for block in matchers:
            if not isinstance(block, dict):
                new_matchers.append(block)
                continue
            new_block = dict(block)
            inner = block.get("hooks")
            if isinstance(inner, list):
                new_inner = []
                for h in inner:
                    if not isinstance(h, dict):
                        new_inner.append(h)
                        continue
                    hh = dict(h)
                    if hh.get("type", "command") == "command" and "command" in hh:
                        hh["command"] = wrap_command(hh["command"], adapter)
                        # Grok 預設 timeout 短；沿用或至少 10
                        hh.setdefault("timeout", 30)
                    new_inner.append(hh)
                new_block["hooks"] = new_inner
            new_matchers.append(new_block)
        out[event] = new_matchers
    return inject_grok_memory_hooks(out, adapter)


def inject_grok_memory_hooks(hooks: dict, adapter: Path) -> dict:
    """Grok-only：產品 memory 路徑閘門（不改 CC 腳本本體）。"""
    write_gate = REPO_SCRIPTS / "grok_memory_write_gate.sh"
    index_check = REPO_SCRIPTS / "grok_memory_index_check.sh"
    if not write_gate.is_file() or not index_check.is_file():
        print("warn: grok memory gate scripts missing; skip inject", file=sys.stderr)
        return hooks

    # 可執行位
    for p in (write_gate, index_check):
        try:
            p.chmod(p.stat().st_mode | 0o111)
        except OSError:
            pass

    pre = list(hooks.get("PreToolUse") or [])
    # 避免重裝重複注入
    pre = [
        b
        for b in pre
        if "grok_memory_write_gate" not in json.dumps(b, ensure_ascii=False)
    ]
    pre.append(
        {
            "matcher": "Write|Edit",
            "hooks": [
                {
                    "type": "command",
                    "command": wrap_command(str(write_gate), adapter),
                    "timeout": 30,
                }
            ],
        }
    )
    hooks["PreToolUse"] = pre

    post = list(hooks.get("PostToolUse") or [])
    post = [
        b
        for b in post
        if "grok_memory_index_check" not in json.dumps(b, ensure_ascii=False)
    ]
    post.append(
        {
            "matcher": "Edit|Write",
            "hooks": [
                {
                    "type": "command",
                    "command": wrap_command(str(index_check), adapter),
                    "timeout": 30,
                }
            ],
        }
    )
    hooks["PostToolUse"] = post
    return hooks


def ensure_adapter_installed(dry_run: bool) -> Path:
    GROK_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    dest = GROK_HOOKS_DIR / ADAPTER_NAME
    if dry_run:
        print(f"[dry-run] symlink/copy {REPO_ADAPTER} → {dest}")
        return dest
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    try:
        dest.symlink_to(REPO_ADAPTER)
        print(f"adapter symlink → {dest}")
    except OSError:
        shutil.copy2(REPO_ADAPTER, dest)
        dest.chmod(0o755)
        print(f"adapter copied → {dest}")
    return dest


def write_hooks_json(transformed: dict, dry_run: bool) -> None:
    payload = {"hooks": transformed}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if dry_run:
        print(f"[dry-run] write {OUT_HOOKS_JSON} ({len(text)} bytes)")
        print(text[:800], "..." if len(text) > 800 else "")
        return
    OUT_HOOKS_JSON.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_HOOKS_JSON}")


def patch_config_toml(disable_claude_hooks: bool, dry_run: bool) -> None:
    if not disable_claude_hooks:
        print("skip config.toml patch (--keep-claude-hooks)")
        return

    block = (
        "\n# cc-to-grok-bridge: avoid double-firing CC hooks "
        "(Grok loads wrapped copies from ~/.grok/hooks/)\n"
        "[compat.claude]\n"
        "hooks = false\n"
    )

    if not GROK_CONFIG.exists():
        content = block.lstrip()
        if dry_run:
            print(f"[dry-run] create {GROK_CONFIG}")
            print(content)
            return
        GROK_CONFIG.write_text(content, encoding="utf-8")
        print(f"created {GROK_CONFIG}")
        return

    text = GROK_CONFIG.read_text(encoding="utf-8")
    if re.search(r"(?m)^\[compat\.claude\]", text):
        # 已有 section：確保 hooks = false
        if re.search(r"(?m)^hooks\s*=\s*false\s*$", text):
            print("config.toml already has hooks = false (or nearby); check [compat.claude] manually if needed")
            # 仍強制寫入 hooks = false 在 section 內
        def repl_section(m: re.Match) -> str:
            body = m.group(0)
            if re.search(r"(?m)^hooks\s*=", body):
                body = re.sub(r"(?m)^hooks\s*=.*$", "hooks = false", body)
            else:
                body = body.rstrip() + "\nhooks = false\n"
            return body

        new_text, n = re.subn(
            r"(?ms)^\[compat\.claude\][^\[]*",
            repl_section,
            text,
            count=1,
        )
        if n == 0:
            new_text = text.rstrip() + "\n" + block
    else:
        new_text = text.rstrip() + "\n" + block

    if dry_run:
        print(f"[dry-run] patch {GROK_CONFIG}")
        print(new_text[-400:])
        return
    GROK_CONFIG.write_text(new_text, encoding="utf-8")
    print(f"patched {GROK_CONFIG} → [compat.claude] hooks = false")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install cc-to-grok-bridge hooks")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--keep-claude-hooks",
        action="store_true",
        help="Do not set compat.claude hooks=false (may double-run hooks)",
    )
    ap.add_argument(
        "--if-stale",
        action="store_true",
        help="Only reinstall when CC settings.json is newer than bridge hooks json",
    )
    args = ap.parse_args()

    if not REPO_ADAPTER.is_file():
        raise SystemExit(f"missing {REPO_ADAPTER}")

    if args.if_stale:
        cc = HOME / ".claude" / "settings.json"
        bridge = GROK_HOOKS_DIR / "cc-bridge-hooks.json"
        if bridge.is_file() and cc.is_file() and cc.stat().st_mtime <= bridge.stat().st_mtime + 1.0:
            print("hooks package up-to-date (--if-stale); skip")
            return 0

    hooks = load_claude_hooks()
    adapter = ensure_adapter_installed(args.dry_run)
    transformed = transform_hooks(hooks, adapter)
    write_hooks_json(transformed, args.dry_run)
    patch_config_toml(disable_claude_hooks=not args.keep_claude_hooks, dry_run=args.dry_run)

    print(
        "\n下一步：\n"
        "  1. 重開 Grok session（從你的 workspace 根目錄）\n"
        "  2. /hooks-trust 若專案 hooks 被擋\n"
        "  3. python3 scripts/bridge_doctor.py\n"
        "  4. 手動驗：請 Grok Read 一個 .env（應被擋）\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
