#!/bin/bash
# grok_memory_index_check.sh — PostToolUse 警示 Grok 端 MEMORY.md 膨脹
# 對齊 CC memory_index_check.sh / CLAUDE.md §5：>145 行或 >22.5KB
# 觸發：~/.grok/memory/**/MEMORY.md 或 ~/.grok/memory/MEMORY.md
# 建立：2026-07-11

INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.tool_input.file_path // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.session_id // .sessionId // "nosession"' 2>/dev/null)

case "$FILE_PATH" in
  */.grok/memory/MEMORY.md|*/.grok/memory/*/MEMORY.md) ;;
  *) exit 0 ;;
esac

[ ! -f "$FILE_PATH" ] && exit 0

LINES=$(wc -l < "$FILE_PATH" 2>/dev/null | tr -d ' ')
BYTES=$(wc -c < "$FILE_PATH" 2>/dev/null | tr -d ' ')
[ -z "$LINES" ] && exit 0

if [ "$LINES" -gt 145 ] || [ "${BYTES:-0}" -gt 23040 ]; then
  STAMP="/tmp/grok_memidx_$(/sbin/md5 -q -s "$SESSION")"
  [ -f "$STAMP" ] && exit 0
  touch "$STAMP"
  # PostToolUse：Grok 多半不 block；stderr 提醒 + allow 決策即可
  echo "📚 Grok MEMORY.md 目前 ${LINES} 行 / ${BYTES} bytes，超過 145 行或 22.5KB。請把冷項目歸檔或拆 topic；勿把整包灌回 CC MEMORY.md。" >&2
fi
exit 0
