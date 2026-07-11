#!/usr/bin/env python3
"""
Install a Grok SessionStart hook that runs bridge_pull.py (fail-open).

Writes: ~/.grok/hooks/cc-bridge-session-pull.json
Does NOT touch ~/.claude/**
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


HOME = Path.home()
REPO = Path(__file__).resolve().parent
PULL = REPO / "bridge_pull.py"
OUT = HOME / ".grok" / "hooks" / "cc-bridge-session-pull.json"


def main() -> int:
    if not PULL.is_file():
        print(f"missing {PULL}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Quiet pull; 120s timeout for first cold sync
    # Resolve workspace at install time: env or cwd (never hardcode a personal path)
    import os
    ws = os.environ.get("CC_GROK_WORKSPACE") or str(Path.cwd())
    cmd = (
        f"{sys.executable} {PULL} "
        f"--workspace \"{ws}\""
    )
    payload = {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CC_GROK_BRIDGE_QUIET=1 {cmd}",
                            "timeout": 180,
                        }
                    ]
                }
            ]
        }
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("SessionStart will run bridge_pull (memory + stale install). Fail-open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
