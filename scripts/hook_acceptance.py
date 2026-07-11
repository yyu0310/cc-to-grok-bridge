#!/usr/bin/env python3
"""
hook_acceptance.py — Grok bridge hook 驗收（adapter 層 + Grok-only gate）

用法（在 bridge repo 根或任意 cwd）：
  python3 scripts/hook_acceptance.py
  python3 scripts/hook_acceptance.py --with-clasp   # 真 push clasp-run-sandbox

設計：敏感路徑只在本檔用 Path 組裝，外層 shell 指令列不出現 .env / clasprc 字樣，
避免 bash_security_gate 誤擋「跑驗收」本身。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
ADAPTER = HOME / ".grok" / "hooks" / "_cc_bridge_adapter.py"
BRIDGE_JSON = HOME / ".grok" / "hooks" / "cc-bridge-hooks.json"
PY = sys.executable
# Workspace under test: $CC_GROK_WORKSPACE or cwd (no personal default path)
VS = Path(os.environ.get("CC_GROK_WORKSPACE", str(Path.cwd()))).expanduser()
# Optional real clasp sandbox for --with-clasp
SANDBOX = Path(os.environ["CC_GROK_CLASP_SANDBOX"]).expanduser() if os.environ.get("CC_GROK_CLASP_SANDBOX") else Path("/nonexistent-clasp-sandbox")


def run_adapter(hook_script: str | Path, payload: dict, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    cmd = [PY, str(ADAPTER), str(hook_script)]
    if extra_args:
        cmd.extend(extra_args)
    r = subprocess.run(
        cmd,
        input=json.dumps(payload, ensure_ascii=False).encode(),
        capture_output=True,
    )
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def run_shell_command(command: str, payload: dict | None = None) -> tuple[int, str, str]:
    r = subprocess.run(
        command,
        shell=True,
        input=json.dumps(payload or {}, ensure_ascii=False).encode(),
        capture_output=True,
    )
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def is_deny(code: int, out: str) -> bool:
    if code == 2:
        return True
    try:
        data = json.loads(out.strip() or "{}")
    except json.JSONDecodeError:
        return "deny" in out.lower()
    if not isinstance(data, dict):
        return False
    if data.get("decision") == "deny":
        return True
    hso = data.get("hookSpecificOutput") or {}
    if isinstance(hso, dict) and hso.get("permissionDecision") == "deny":
        return True
    return False


def ok(name: str, cond: bool, detail: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-clasp", action="store_true", help="真 clasp push sandbox")
    args = ap.parse_args()

    results: list[bool] = []
    if not ADAPTER.is_file() and not ADAPTER.is_symlink():
        print("FAIL: adapter missing", ADAPTER)
        return 1
    if not BRIDGE_JSON.is_file():
        print("FAIL: bridge hooks json missing")
        return 1

    hooks_doc = json.loads(BRIDGE_JSON.read_text(encoding="utf-8"))
    blob = json.dumps(hooks_doc, ensure_ascii=False)
    results.append(ok("bridge has grok_memory_write_gate", "grok_memory_write_gate" in blob))
    results.append(ok("bridge has grok_memory_index_check", "grok_memory_index_check" in blob))

    # --- adapter unit ---
    code, out, _ = run_adapter(
        "/bin/bash",
        {},
        [
            "-lc",
            'echo \'{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Current time: MARKER_ACC"}}\'' ,
        ],
    )
    results.append(
        ok(
            "adapter passthrough additionalContext",
            code == 0 and "MARKER_ACC" in out,
            out[:100].replace("\n", " "),
        )
    )

    code, out, _ = run_adapter(
        "/bin/bash",
        {},
        [
            "-lc",
            'echo \'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"ACC_DENY"}}\'' ,
        ],
    )
    results.append(
        ok(
            "adapter permissionDecision deny→Grok deny",
            code == 2 and is_deny(code, out) and "ACC_DENY" in out,
            out[:120],
        )
    )

    code, out, err = run_adapter(
        "/bin/bash",
        {},
        [
            "-lc",
            'echo \'{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"ACC_ASK"}}\'' ,
        ],
    )
    compact = out.replace(" ", "")
    results.append(
        ok(
            "adapter permissionDecision ask→allow",
            code == 0 and ('"decision":"allow"' in compact),
            f"out={out[:80]} err={err[:60]}",
        )
    )

    # --- CC hooks via adapter ---
    sens_read = HOME / ".claude" / "hooks" / "block_sensitive_read.sh"
    clasprc = HOME / ".clasprc.json"
    env_fake = VS / ".env"
    claude_md = VS / "CLAUDE.md"

    code, out, err = run_adapter(
        sens_read,
        {"toolName": "read_file", "toolInput": {"target_file": str(clasprc)}},
    )
    results.append(ok("block_sensitive_read deny clasprc", is_deny(code, out) or is_deny(code, err), f"code={code}"))

    code, out, err = run_adapter(
        sens_read,
        {"toolName": "read_file", "toolInput": {"target_file": str(claude_md)}},
    )
    results.append(ok("block_sensitive_read allow CLAUDE.md", not is_deny(code, out), f"code={code}"))

    code, out, err = run_adapter(
        sens_read,
        {"toolName": "read_file", "toolInput": {"target_file": str(env_fake)}},
    )
    results.append(ok("block_sensitive_read deny .env path", is_deny(code, out) or is_deny(code, err), f"code={code}"))

    bash_gate = HOME / ".claude" / "hooks" / "bash_security_gate.sh"
    code, out, err = run_adapter(
        bash_gate,
        {"toolName": "run_terminal_command", "toolInput": {"command": "echo hook-smoke-ok"}},
    )
    results.append(ok("bash_security_gate allow echo", not is_deny(code, out), f"code={code}"))

    pre_push = HOME / ".claude" / "hooks" / "pre_push_safety.sh"
    code, out, err = run_adapter(
        pre_push,
        {"toolName": "run_terminal_command", "toolInput": {"command": "echo not-a-push"}},
    )
    results.append(ok("pre_push_safety non-push allow", not is_deny(code, out), f"code={code}"))

    mem_gate = HOME / ".claude" / "hooks" / "memory_write_gate.sh"
    code, out, err = run_adapter(
        mem_gate,
        {
            "toolName": "search_replace",
            "toolInput": {"file_path": str(VS / "README.md"), "old_string": "a", "new_string": "b"},
            "session_id": "acc-non-mem",
        },
    )
    results.append(ok("CC memory_write_gate non-memory allow", not is_deny(code, out), f"code={code}"))

    # CC memory path first hit → deny
    cc_mem = HOME / ".claude" / "projects" / "dummy-acc" / "memory" / "note.md"
    stamp_glob = Path("/tmp")
    # clean stamps for this session id
    for p in stamp_glob.glob("claude_memory_gate_*"):
        try:
            p.unlink()
        except OSError:
            pass
    code, out, err = run_adapter(
        mem_gate,
        {
            "toolName": "write",
            "toolInput": {"file_path": str(cc_mem), "content": "x"},
            "session_id": "acc-cc-mem-1",
        },
    )
    results.append(ok("CC memory_write_gate first deny", is_deny(code, out), out[:100]))

    # Grok memory gate
    repo = Path(__file__).resolve().parent
    grok_gate = repo / "grok_memory_write_gate.sh"
    for p in Path("/tmp").glob("grok_memory_gate_*"):
        try:
            p.unlink()
        except OSError:
            pass
    gpath = HOME / ".grok" / "memory" / "acc_gate_probe.md"
    code, out, err = run_adapter(
        grok_gate,
        {
            "toolName": "write",
            "toolInput": {"file_path": str(gpath), "content": "probe"},
            "session_id": "acc-grok-mem-1",
        },
    )
    results.append(ok("grok_memory_write_gate 1st deny", is_deny(code, out), out[:120]))

    code, out, err = run_adapter(
        grok_gate,
        {
            "toolName": "write",
            "toolInput": {"file_path": str(gpath), "content": "probe2"},
            "session_id": "acc-grok-mem-1",
        },
    )
    # 第二次 ask → adapter 翻 allow
    results.append(
        ok(
            "grok_memory_write_gate 2nd ask→allow",
            not is_deny(code, out) and code == 0,
            out[:100],
        )
    )

    # from_cc first deny
    for p in Path("/tmp").glob("grok_memory_gate_*"):
        try:
            p.unlink()
        except OSError:
            pass
    from_cc = HOME / ".grok" / "memory" / "example-workspace-a1b2c3d4" / "_from_cc" / "probe.md"
    code, out, err = run_adapter(
        grok_gate,
        {
            "toolName": "write",
            "toolInput": {"file_path": str(from_cc), "content": "x"},
            "session_id": "acc-from-cc",
        },
    )
    results.append(ok("grok_memory_write_gate _from_cc deny", is_deny(code, out), out[:120]))

    # UserPrompt live time inject from bridge json
    ups = hooks_doc.get("hooks", {}).get("UserPromptSubmit") or []
    time_cmd = None
    for block in ups:
        for h in block.get("hooks") or []:
            c = h.get("command") or ""
            if "additionalContext" in c or "Current time" in c or "date" in c:
                time_cmd = c
                break
        if time_cmd:
            break
    if time_cmd:
        code, out, err = run_shell_command(time_cmd, {})
        results.append(
            ok(
                "UserPrompt time inject via bridge command",
                code == 0 and ("Current time" in out or "additionalContext" in out),
                out[:140].replace("\n", " "),
            )
        )
    else:
        results.append(ok("UserPrompt time inject found in json", False))

    # PostToolUse non-gs clasp skip
    clasp_hook = HOME / ".claude" / "hooks" / "auto_clasp_push.sh"
    code, out, err = run_adapter(
        clasp_hook,
        {
            "toolName": "search_replace",
            "toolInput": {"file_path": str(VS / "foo.py")},
        },
    )
    results.append(ok("auto_clasp_push skip non-gs", code == 0, f"code={code}"))

    # lifecycle tool_guide
    tgr = HOME / ".claude" / "hooks" / "tool_guide_reminder.sh"
    code, out, err = run_adapter(tgr, {"hookEventName": "Stop"})
    results.append(ok("tool_guide_reminder Stop", code == 0, f"code={code}"))

    # commitment check
    cpc = HOME / ".claude" / "hooks" / "commitment_persistence_check.sh"
    code, out, err = run_adapter(
        cpc,
        {"hookEventName": "Stop", "last_assistant_message": "done", "tool_use": []},
    )
    results.append(ok("commitment_persistence_check Stop", code == 0, f"code={code}"))

    # auto_qa_python on temp py
    aqa = HOME / ".claude" / "hooks" / "auto_qa_python.sh"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("print(1)\n")
        tmp_py = f.name
    try:
        code, out, err = run_adapter(
            aqa,
            {"toolName": "write", "toolInput": {"file_path": tmp_py}},
        )
        results.append(ok("auto_qa_python temp py", code == 0, f"code={code}"))
    finally:
        try:
            os.unlink(tmp_py)
        except OSError:
            pass

    if args.with_clasp:
        gs = SANDBOX / "main.gs"
        if not (SANDBOX / ".clasp.json").is_file():
            results.append(ok("clasp sandbox exists", False, str(SANDBOX)))
        else:
            code, out, err = run_adapter(
                clasp_hook,
                {
                    "toolName": "search_replace",
                    "toolInput": {"file_path": str(gs)},
                },
            )
            combined = out + err
            results.append(
                ok(
                    "auto_clasp_push sandbox real push",
                    code == 0 and ("Pushed" in combined or "push" in combined.lower()),
                    combined[:200].replace("\n", " "),
                )
            )

    # product memory config
    cfg = (HOME / ".grok" / "config.toml").read_text(encoding="utf-8")
    results.append(ok("product memory enabled=true", "[memory]" in cfg and "enabled = true" in cfg))

    passed = sum(1 for x in results if x)
    total = len(results)
    print(f"\n=== {passed}/{total} PASS ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
