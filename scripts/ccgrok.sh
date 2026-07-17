#!/usr/bin/env bash
# ccgrok: drive Grok Build (grok -p) with the research-method prefix, from a clean cwd.
# Usage: ccgrok.sh "your question"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="$SCRIPT_DIR/../research-prefix.md"
GROK="$(command -v grok || echo "$HOME/.grok/bin/grok")"
QUESTION="${1:?usage: ccgrok.sh \"question\"}"

# Runnable checks: fail loudly rather than sending a bare prompt or hitting a missing binary.
[ -f "$PREFIX" ] || { echo "research-prefix.md not found at $PREFIX" >&2; exit 1; }
[ -x "$GROK" ] || { echo "grok CLI not found (install Grok Build)" >&2; exit 1; }

# Clean cwd so no project CLAUDE.md / .grok/rules leak into a pure research query.
cd "$(mktemp -d)"

# Search-enabling flags for Grok headless; disallowed-tools keeps the run read-only
# (no shell, no file writes), so auto-approve cannot touch local files.
exec "$GROK" -p "$(cat "$PREFIX")

$QUESTION" --no-plan --always-approve --disallowed-tools "run_terminal_cmd,write,search_replace" --output-format plain
