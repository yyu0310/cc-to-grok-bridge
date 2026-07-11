#!/usr/bin/env python3
"""
hook_adapter.py — 把 Grok hook stdin 正規成 Claude Code 腳本習慣的 JSON，
再呼叫原 hook；若原 hook 以 exit 2 拒絕，改輸出 Grok 可懂的 deny JSON。

用法：
  python3 hook_adapter.py /path/to/original_hook.sh [args...]

環境：
  CC_GROK_BRIDGE_DEBUG=1  → 除錯訊息印 stderr
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


# Grok 工具名 → Claude 慣用名（腳本內常硬比對 tool 字串）
GROK_TO_CLAUDE_TOOL = {
    "run_terminal_command": "Bash",
    "read_file": "Read",
    "search_replace": "Edit",  # Write/Edit 在 CC 常共用路徑邏輯；Edit 較通用
    "write": "Write",
    "grep": "Grep",
    "list_dir": "Glob",  # Glob 腳本常查 path/pattern；list_dir 近似
    "web_search": "WebSearch",
    "web_fetch": "WebFetch",
    "spawn_subagent": "Task",
    "open_page": "WebFetch",
}


def debug(msg: str) -> None:
    if os.environ.get("CC_GROK_BRIDGE_DEBUG"):
        print(f"[cc-to-grok-bridge] {msg}", file=sys.stderr)


def first_key(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def normalize_tool_input(tool_claude: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """補齊 CC hook 習慣的欄位名，不刪 Grok 原欄位。"""
    out = dict(tool_input)

    # Read: target_file → file_path
    path = first_key(out, "file_path", "target_file", "path", "filePath", "targetFile")
    if path is not None:
        out.setdefault("file_path", path)
        out.setdefault("path", path)

    # Bash: command
    cmd = first_key(out, "command", "cmd")
    if cmd is not None:
        out.setdefault("command", cmd)

    # Grep/Glob-ish
    for src, dest in (
        ("pattern", "pattern"),
        ("glob", "glob"),
        ("target_directory", "path"),
    ):
        if src in out and dest not in out:
            out[dest] = out[src]

    # search_replace / write content paths
    if "old_string" in out or "new_string" in out or "content" in out:
        out.setdefault("file_path", first_key(out, "file_path", "path", default=""))

    return out


def to_claude_envelope(raw: dict[str, Any]) -> dict[str, Any]:
    tool_raw = first_key(raw, "tool_name", "toolName", default="") or ""
    tool_claude = GROK_TO_CLAUDE_TOOL.get(str(tool_raw), str(tool_raw))

    tool_input = first_key(raw, "tool_input", "toolInput", default={}) or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    tool_input = normalize_tool_input(tool_claude, tool_input)

    # 保留原 payload，並覆寫 CC 慣用鍵（腳本優先讀 snake_case）
    env = dict(raw)
    env["tool_name"] = tool_claude
    env["toolName"] = tool_raw or tool_claude
    env["tool_input"] = tool_input
    env["toolInput"] = tool_input

    # 常見 session / cwd 別名
    cwd = first_key(raw, "cwd", "CWD", "workspaceRoot", "workspace_root")
    if cwd:
        env.setdefault("cwd", cwd)

    return env


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: hook_adapter.py <hook-script> [args...]", file=sys.stderr)
        return 1

    hook_script = sys.argv[1]
    hook_args = sys.argv[2:]

    raw_stdin = sys.stdin.read()
    try:
        raw = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError:
        # 非 JSON 就原樣轉發
        raw = {}
        payload_bytes = raw_stdin.encode("utf-8")
        env_for_child = None
    else:
        if not isinstance(raw, dict):
            raw = {}
        claude_env = to_claude_envelope(raw)
        debug(f"tool {first_key(raw, 'toolName', 'tool_name')} → {claude_env.get('tool_name')}")
        payload_bytes = json.dumps(claude_env, ensure_ascii=False).encode("utf-8")
        env_for_child = None

    # 繼承環境；確保 CLAUDE_PROJECT_DIR 若 Grok 有設則可用
    child_env = os.environ.copy()

    try:
        proc = subprocess.run(
            [hook_script, *hook_args],
            input=payload_bytes,
            capture_output=True,
            env=child_env,
        )
    except FileNotFoundError:
        print(
            json.dumps(
                {
                    "decision": "deny",
                    "reason": f"cc-to-grok-bridge: hook not found: {hook_script}",
                },
                ensure_ascii=False,
            )
        )
        return 2
    except PermissionError:
        print(
            json.dumps(
                {
                    "decision": "deny",
                    "reason": f"cc-to-grok-bridge: hook not executable: {hook_script}",
                },
                ensure_ascii=False,
            )
        )
        return 2

    # 透傳 stderr（CC 攔截理由在這）
    if proc.stderr:
        sys.stderr.buffer.write(proc.stderr)
        sys.stderr.buffer.flush()

    stdout = proc.stdout or b""
    code = proc.returncode

    # 若子程序已輸出可辨 JSON：
    # - Grok decision deny/allow → 透傳
    # - CC hookSpecificOutput.permissionDecision deny/ask → 翻成 Grok decision
    # - UserPrompt additionalContext 等 → 透傳
    text = stdout.decode("utf-8", errors="replace").strip()
    if text:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                hso = data.get("hookSpecificOutput")
                if isinstance(hso, dict):
                    perm = hso.get("permissionDecision")
                    reason = (
                        hso.get("permissionDecisionReason")
                        or data.get("systemMessage")
                        or "Blocked by Claude Code hook"
                    )
                    if perm == "deny":
                        print(
                            json.dumps(
                                {"decision": "deny", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                        return 2
                    if perm == "ask":
                        # Grok PreToolUse 無 CC 式 ask 視窗：第二次起放行，
                        # 交由 permission_mode／對話審核；理由印 stderr 可見。
                        print(reason, file=sys.stderr)
                        print(json.dumps({"decision": "allow"}, ensure_ascii=False))
                        return 0

                if "decision" in data:
                    sys.stdout.write(text if text.endswith("\n") else text + "\n")
                    return 0 if data.get("decision") != "deny" else 2

                if "hookSpecificOutput" in data or "systemMessage" in data:
                    # 例如 UserPromptSubmit additionalContext
                    sys.stdout.write(text if text.endswith("\n") else text + "\n")
                    return 0 if code != 2 else 2
        except json.JSONDecodeError:
            pass

    if code == 2:
        reason = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        if not reason:
            reason = "Blocked by Claude Code hook (exit 2)"
        # 多行 stderr 取最後非空行較像「理由」
        lines = [ln.strip() for ln in reason.splitlines() if ln.strip()]
        if lines:
            reason = lines[-1]
        print(
            json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False)
        )
        return 2

    # 允許：可輸出 allow，或靜默 exit 0
    if text and not text.startswith("{"):
        # 非 JSON 的 stdout 在 Grok PreToolUse 多半無用；仍透傳以免腳本依賴
        sys.stdout.buffer.write(stdout)
    elif code == 0:
        print(json.dumps({"decision": "allow"}))
    else:
        # 非 0/2：Grok fail-open；對齊不擋
        debug(f"hook exit {code}; fail-open allow")
        print(json.dumps({"decision": "allow"}))

    return 0 if code in (0, 2) else 0


if __name__ == "__main__":
    sys.exit(main())
