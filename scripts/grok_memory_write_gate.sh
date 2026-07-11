#!/bin/bash
# grok_memory_write_gate.sh — PreToolUse (Write|Edit) 攔截 Grok 產品 memory 寫入
# 對齊 CC memory_write_gate.sh 精神（hook.md §7 / CLAUDE.md §5）：
#   第一次 deny；同 session 同檔重試 → ask（adapter 在 Grok 上翻成第二次 allow + stderr 理由）
# 路徑：~/.grok/memory/**（產品 memory + bridge 三區）
# 不修改 ~/.claude/hooks/*（Grok-only 腳本）
# 建立：2026-07-11

input=$(cat)
file_path=$(printf '%s' "$input" | /usr/bin/jq -r '.tool_input.file_path // empty' 2>/dev/null)
session_id=$(printf '%s' "$input" | /usr/bin/jq -r '.session_id // .sessionId // "nosession"' 2>/dev/null)
[ -z "$session_id" ] && session_id="nosession"

# 只攔 Grok memory 樹；其他路徑放行（CC 路徑仍由 memory_write_gate.sh 攔）
case "$file_path" in
  */.grok/memory/*) ;;
  "$HOME"/.grok/memory/*) ;;
  *) exit 0 ;;
esac

# _from_cc 是 pull 鏡像：代理不該手寫；第一次也 deny（訊息不同）
is_from_cc=0
case "$file_path" in
  */_from_cc/*) is_from_cc=1 ;;
esac

stamp="/tmp/grok_memory_gate_$(/sbin/md5 -q -s "${session_id}:${file_path}")"

if [ ! -f "$stamp" ]; then
  touch "$stamp"
  if [ "$is_from_cc" -eq 1 ]; then
    reason="🧠 Grok memory 寫入攔截（_from_cc 鏡像）。此區是 CC→Grok pull 副本，會被下次 pull 覆蓋；不要手寫。跨 harness 共用事實請寫 general/（候選 push）或專案資料夾；Grok-only 寫 grok/。"
  else
    reason="🧠 Grok memory 寫入攔截（第一次一律自動拒絕）。對齊 CLAUDE.md §5：memory 只放跨對話都要記住的行為指引／大專案一行指標，細節進專案資料夾或工作日誌；瑣碎任務、當日工單、整包架構快照不進 memory。請先確認有無專案路徑可寫。若確實該進 memory：general/＝可候選 push 到 CC（需 source: grok-build）；grok/＝永不 push；全域 MEMORY.md 當未分類／L2。向用戶敘明原因後再重試同一寫入。"
  fi
  /usr/bin/jq -n --arg reason "$reason" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
else
  /usr/bin/jq -n --arg reason "第二次 Grok memory 寫入請求：$file_path。請確認已向用戶敘明理由，且內容符合 §5（索引／跨對話指引），不是瑣事。" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$reason}}'
fi
exit 0
