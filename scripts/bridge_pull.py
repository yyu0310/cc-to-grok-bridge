#!/usr/bin/env python3
"""
bridge_pull.py — 動態同步「拉」：CC → Grok（fail-open，適合 SessionStart）

預設：
  1. memory_sync.py
  2. 若 CC settings.json 比 bridge hooks json 新 → install_bridge.py
  3. 不跑完整 doctor（太慢）；--doctor 可加

環境：
  CC_GROK_BRIDGE_QUIET=1  少印

用法：
  python3 bridge_pull.py
  python3 bridge_pull.py --workspace ~/path/to/your-workspace
  python3 bridge_pull.py --no-install
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


HOME = Path.home()
REPO = Path(__file__).resolve().parent
def default_workspace() -> Path:
    """Prefer $CC_GROK_WORKSPACE, else current working directory."""
    env = os.environ.get("CC_GROK_WORKSPACE")
    if env:
        return Path(env).expanduser()
    return Path.cwd()

DEFAULT_WS = default_workspace()


def log(msg: str) -> None:
    if os.environ.get("CC_GROK_BRIDGE_QUIET"):
        return
    print(f"[bridge_pull] {msg}", flush=True)


def run(args: list[str], timeout: int = 120) -> int:
    try:
        r = subprocess.run(args, cwd=str(REPO), timeout=timeout)
        return r.returncode
    except subprocess.TimeoutExpired:
        log(f"timeout: {args}")
        return 124
    except OSError as e:
        log(f"os error: {e}")
        return 1


def settings_stale() -> bool:
    cc = HOME / ".claude" / "settings.json"
    bridge = HOME / ".grok" / "hooks" / "cc-bridge-hooks.json"
    if not bridge.is_file():
        return True
    if not cc.is_file():
        return False
    return cc.stat().st_mtime > bridge.stat().st_mtime + 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(DEFAULT_WS))
    ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--doctor", action="store_true")
    args = ap.parse_args()
    ws = str(Path(args.workspace).expanduser())

    # 1) memory pull
    log("memory_sync…")
    code = run(
        [sys.executable, str(REPO / "memory_sync.py"), "--workspace", ws],
        timeout=180,
    )
    if code != 0:
        log(f"memory_sync exit {code} (continue)")

    # 2) re-wrap hooks if CC settings newer
    if not args.no_install and settings_stale():
        log("CC settings newer than bridge hooks → install_bridge…")
        code = run([sys.executable, str(REPO / "install_bridge.py")], timeout=60)
        if code != 0:
            log(f"install_bridge exit {code} (continue)")
    else:
        log("hooks package fresh (skip install)")

    if args.doctor:
        log("doctor…")
        run(
            [sys.executable, str(REPO / "bridge_doctor.py"), "--workspace", ws],
            timeout=120,
        )

    log("done")
    return 0  # SessionStart 永不擋開場


if __name__ == "__main__":
    sys.exit(main())
