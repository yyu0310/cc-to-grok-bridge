#!/usr/bin/env python3
"""Shared paths for Grok memory hard isolation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HOME = Path.home()


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", name, flags=re.UNICODE)
    return re.sub(r"-+", "-", s).strip("-") or "workspace"


def cc_project_hash_name(workspace: Path) -> str:
    return str(workspace.resolve()).replace("/", "-").replace(" ", "-")


def cc_memory_dir(workspace: Path) -> Path:
    return HOME / ".claude" / "projects" / cc_project_hash_name(workspace) / "memory"


def grok_project_memory_dir(workspace: Path) -> Path:
    """Prefer existing bridge meta dir; else slug-hash8."""
    base = HOME / ".grok" / "memory"
    if base.is_dir():
        for d in base.iterdir():
            if not d.is_dir():
                continue
            meta = d / "_cc_bridge_meta.json"
            if meta.is_file():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    if data.get("workspace") == str(workspace.resolve()):
                        return d
                except (json.JSONDecodeError, OSError):
                    pass
    identity = str(workspace.resolve())
    h8 = hashlib.sha256(identity.encode()).hexdigest()[:8]
    return base / f"{slugify(workspace.name)}-{h8}"


def ensure_layout(root: Path) -> dict[str, Path]:
    """
    Hard isolation:
      _from_cc/  — pull mirror from CC (overwritten by pull)
      general/   — Grok-authored, candidates for push to CC
      grok/      — Grok-only, never push
    """
    paths = {
        "root": root,
        "from_cc": root / "_from_cc",
        "general": root / "general",
        "grok": root / "grok",
    }
    for p in paths.values():
        if p == root:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.mkdir(parents=True, exist_ok=True)
    return paths
