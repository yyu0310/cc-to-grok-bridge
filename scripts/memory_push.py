#!/usr/bin/env python3
"""
memory_push.py — Grok general/ → Claude Code memory（受限 push）

只處理：
  ~/.grok/memory/<project>/general/*.md

寫入：
  ~/.claude/projects/…/memory/<stem>.md
  並在 MEMORY.md 加一行指標（若尚未存在且紅線內）

不處理：
  grok/、_from_cc/、無標籤且不在 general/ 的檔

標籤契約（frontmatter 建議）：
  source: grok-build
  scope: general
  harness: shared

用法：
  python3 memory_push.py --dry-run
  python3 memory_push.py
  python3 memory_push.py --file feedback_xxx.md
"""

from __future__ import annotations

import os
import argparse
import re
import sys
from datetime import date
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
# CLAUDE.md §5 / 05_維護協議
MAX_LINES = 145
MAX_BYTES = 22500

FORBIDDEN_STEMS = {
    "MEMORY",
    "MEMORY_ARCHIVE",
    "MEMORY_ORBIT",
}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, parts[2].lstrip("\n")


def ensure_push_frontmatter(text: str, stem: str) -> str:
    meta, body = parse_frontmatter(text)
    meta.setdefault("source", "grok-build")
    meta.setdefault("scope", "general")
    meta.setdefault("harness", "shared")
    meta.setdefault("name", stem.replace("_", "-"))
    if "description" not in meta:
        first = next((ln.strip() for ln in body.splitlines() if ln.strip() and not ln.startswith("#")), "")
        meta["description"] = first[:120] if first else stem
    meta["synced_to_cc"] = "true"
    meta["synced_date"] = date.today().isoformat()
    # rebuild
    lines = ["---"]
    for k in ("name", "description", "source", "scope", "harness", "synced_to_cc", "synced_date"):
        if k in meta:
            lines.append(f"{k}: {meta[k]}")
    for k, v in meta.items():
        if k not in ("name", "description", "source", "scope", "harness", "synced_to_cc", "synced_date"):
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    # 檔首可見標記（給人與 AI）
    if "source: grok-build" not in body and "（來源：Grok Build" not in body[:200]:
        body = f"> 來源：Grok Build bridge push（`source: grok-build`）。\n\n{body}"
    return "\n".join(lines) + body


def index_line_from_file(stem: str, text: str) -> str:
    meta, body = parse_frontmatter(text)
    title = meta.get("description") or meta.get("name") or stem
    # 薄指標：一行
    return f"- [{title}]({stem}.md) — Grok Build 寫入（source: grok-build）"


def memory_redline_ok(mem_path: Path, extra_line: str) -> tuple[bool, str]:
    if not mem_path.is_file():
        return False, "MEMORY.md missing"
    raw = mem_path.read_text(encoding="utf-8")
    lines = raw.count("\n") + (0 if raw.endswith("\n") or not raw else 1)
    size = len(raw.encode("utf-8"))
    extra_b = len((extra_line + "\n").encode("utf-8"))
    if lines + 1 > MAX_LINES:
        return False, f"MEMORY.md lines would exceed {MAX_LINES} ({lines}+1)"
    if size + extra_b > MAX_BYTES:
        return False, f"MEMORY.md bytes would exceed {MAX_BYTES} ({size}+{extra_b})"
    return True, "ok"


def secret_scan(text: str) -> list[str]:
    """Detect secret-like substrings (patterns split to avoid self-flagging scanners)."""
    hits = []
    # joined at runtime — do not store full provider key prefixes as literals
    patterns = [
        "".join(("sk", "-", "ant", "-")),
        "".join(("sk", "-", "proj", "-")),
        "".join(("ghp", "_")) + r"[A-Za-z0-9]+",
        "".join(("github", "_", "pat", "_")),
        r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY",
        "".join(("AI", "za")) + r"[0-9A-Za-z_-]{20,}",
    ]
    for pat in patterns:
        if re.search(pat, text):
            hits.append(pat)
    return hits


def push_one(
    src: Path,
    cc_dir: Path,
    dry: bool,
    force: bool,
) -> str:
    stem = src.stem
    if stem in FORBIDDEN_STEMS or stem.startswith("MEMORY"):
        return f"skip forbidden stem {stem}"

    text = src.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)
    scope = meta.get("scope", "general")
    if scope == "grok-specific" or meta.get("harness") == "grok":
        return f"skip {stem}: marked grok-specific"

    hits = secret_scan(text)
    if hits and not force:
        return f"ABORT {stem}: secret-like pattern {hits}"

    out_text = ensure_push_frontmatter(text, stem)
    dest = cc_dir / f"{stem}.md"
    idx_line = index_line_from_file(stem, out_text)
    mem_path = cc_dir / "MEMORY.md"

    already = dest.is_file() and dest.read_text(encoding="utf-8") == out_text
    mem_raw = mem_path.read_text(encoding="utf-8") if mem_path.is_file() else ""
    linked = f"]({stem}.md)" in mem_raw

    if dry:
        ok, reason = memory_redline_ok(mem_path, idx_line) if not linked else (True, "already linked")
        return (
            f"[dry-run] {stem}: write {dest.name} "
            f"({'same' if already else 'new/update'}); "
            f"index={'skip' if linked else ('add' if ok else 'BLOCKED '+reason)}"
        )

    dest.write_text(out_text, encoding="utf-8")
    print(f"wrote CC {dest}")

    if not linked:
        ok, reason = memory_redline_ok(mem_path, idx_line)
        if not ok:
            print(f"WARN index not updated: {reason}", file=sys.stderr)
            print("  topic file written; add MEMORY.md line manually or archive cold items first")
            return f"pushed body only {stem}"
        # append under a small section for Grok if present, else end
        section = "\n## From Grok Build\n"
        if "## From Grok Build" in mem_raw:
            # append after section header block - simple: append line before ARCHIVE note if any
            mem_raw = mem_raw.rstrip() + "\n" + idx_line + "\n"
        else:
            mem_raw = mem_raw.rstrip() + "\n" + section + idx_line + "\n"
        mem_path.write_text(mem_raw, encoding="utf-8")
        print(f"updated MEMORY.md (+1 line for {stem})")
    else:
        print(f"MEMORY.md already links {stem}.md")

    # mark local
    src.write_text(out_text, encoding="utf-8")
    return f"pushed {stem}"


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="Push Grok general/ memory to CC")
    ap.add_argument("--workspace", default=str(DEFAULT_WS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", action="append", default=[], help="Only these basenames in general/")
    ap.add_argument("--force", action="store_true", help="Allow secret-like patterns (dangerous)")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    cc_dir = cc_memory_dir(workspace)
    if not cc_dir.is_dir():
        print(f"[ERROR] CC memory missing: {cc_dir}", file=sys.stderr)
        return 1

    root = grok_project_memory_dir(workspace)
    paths = ensure_layout(root)
    general = paths["general"]

    if args.file:
        files = [general / f for f in args.file]
    else:
        files = sorted(general.glob("*.md"))

    if not files:
        print(f"no files in {general} (put general notes there first)")
        return 0

    results = []
    for f in files:
        if not f.is_file():
            results.append(f"missing {f}")
            continue
        results.append(push_one(f, cc_dir, args.dry_run, args.force))

    for r in results:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
