#!/usr/bin/env python3
"""
memory_sync.py — 單向 pull：Claude Code memory → Grok `_from_cc/`

Source of truth: CC
  ~/.claude/projects/<project-hash>/memory/*.md

Target (hard isolation):
  ~/.grok/memory/<slug>-<hash8>/_from_cc/*.md
  不碰 general/、grok/（Grok 自寫區）

衝突：CC 蓋 _from_cc 同名檔。
"""

from __future__ import annotations

import os
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from memory_layout import (
    HOME,
    cc_memory_dir,
    ensure_layout,
    grok_project_memory_dir,
)

def default_workspace() -> Path:
    """Prefer $CC_GROK_WORKSPACE, else current working directory."""
    env = os.environ.get("CC_GROK_WORKSPACE")
    if env:
        return Path(env).expanduser()
    return Path.cwd()

DEFAULT_WS = default_workspace()


def list_cc_md_files(cc_dir: Path) -> list[Path]:
    if not cc_dir.is_dir():
        return []
    out = []
    for p in sorted(cc_dir.glob("*.md")):
        if ".bak" in p.name:
            continue
        out.append(p)
    return out


def write_pointer(workspace: Path, target_root: Path, n_from_cc: int, dry: bool) -> None:
    rules = workspace / ".grok" / "rules"
    pointer = rules / "cc-memory-pointer.md"
    body = f"""# CC memory 指標（bridge 自動產生 · Grok-only）

- **不進 Claude 上下文**（本檔在 `.grok/rules/`）
- **CC SoT**：`~/.claude/projects/…/memory/`
- **Grok 目錄硬隔離**（`{target_root}`）：
  - `_from_cc/` — pull 鏡像（{n_from_cc} 檔，可被 pull 覆蓋）
  - `general/` — Grok 寫的、**可 push 到 CC** 的候選
  - `grok/` — **永不 push**（Grok-specific）
- **更新**：`python3 scripts/memory_sync.py`（pull）／`python3 scripts/memory_push.py`（general→CC）
- 架構：`cc-to-grok-bridge/architecture.md` §6
"""
    if dry:
        print(f"[dry-run] write pointer {pointer}")
        return
    rules.mkdir(parents=True, exist_ok=True)
    pointer.write_text(body, encoding="utf-8")
    print(f"wrote pointer {pointer}")


def migrate_flat_mirror(root: Path, from_cc: Path, dry: bool) -> int:
    """若舊版把 md 平舖在 root，移入 _from_cc（不碰 general/grok）。"""
    moved = 0
    for p in list(root.glob("*.md")):
        if p.name.startswith("_"):
            continue
        dest = from_cc / p.name
        if dry:
            print(f"[dry-run] migrate {p.name} → _from_cc/")
            moved += 1
            continue
        data = p.read_bytes()
        if not dest.exists() or dest.read_bytes() != data:
            dest.write_bytes(data)
        p.unlink()
        moved += 1
        print(f"migrate {p.name} → _from_cc/")
    return moved


def sync(workspace: Path, cc_dir: Path, dry: bool) -> dict:
    files = list_cc_md_files(cc_dir)
    if not files:
        print(f"[ERROR] no memory md in {cc_dir}", file=sys.stderr)
        return {"error": "empty"}

    root = grok_project_memory_dir(workspace)
    paths = ensure_layout(root)
    from_cc = paths["from_cc"]

    migrate_flat_mirror(root, from_cc, dry)

    counts = {"copied": 0, "skipped_same": 0, "target": str(from_cc)}

    for src in files:
        dest = from_cc / src.name
        data = src.read_bytes()
        if dest.is_file() and dest.read_bytes() == data:
            counts["skipped_same"] += 1
            continue
        if dry:
            print(f"[dry-run] copy {src.name}")
        else:
            dest.write_bytes(data)
            print(f"copy {src.name} → {dest}")
        counts["copied"] += 1

    write_pointer(workspace, root, len(files), dry)

    meta = {
        "workspace": str(workspace.resolve()),
        "cc_memory_dir": str(cc_dir.resolve()),
        "target_root": str(root),
        "from_cc": str(from_cc),
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "files": [p.name for p in files],
        "policy": "unidirectional CC→Grok _from_cc; general/ and grok/ untouched",
        "layout": ["_from_cc", "general", "grok"],
    }
    meta_path = root / "_cc_bridge_meta.json"
    if not dry:
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {meta_path}")
    counts["files"] = len(files)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(DEFAULT_WS))
    ap.add_argument("--cc-memory-dir", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    cc_dir = (
        Path(args.cc_memory_dir).expanduser().resolve()
        if args.cc_memory_dir
        else cc_memory_dir(workspace)
    )
    if not cc_dir.is_dir():
        print(f"[ERROR] CC memory dir not found: {cc_dir}", file=sys.stderr)
        return 1

    print(f"workspace={workspace}")
    print(f"cc_dir={cc_dir}")
    # import path: run from scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    result = sync(workspace, cc_dir, args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    # ensure sibling import when invoked as script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
