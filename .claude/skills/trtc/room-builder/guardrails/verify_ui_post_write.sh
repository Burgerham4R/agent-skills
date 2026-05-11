#!/usr/bin/env bash
# verify_ui_post_write.sh — PostToolUse(Write|Edit) hook glue.
#
# Reads Claude Code's hook stdin JSON, extracts tool_input.file_path,
# and runs trtc_verify_ui.py --file on it. If the path isn't a .vue
# under the user project_root, the verifier itself no-ops, so this
# script just forwards.
#
# Exit code is whatever the verifier returns (0 pass, 2 fail).
# The verifier writes actionable stderr that Claude Code will surface
# back to the model.
set -euo pipefail

GUARDRAILS_DIR="$(cd "$(dirname "$0")" && pwd)"

# Hook stdin is JSON: { tool_input: { file_path: "..." }, ... }
# jq -r prints empty string on missing field, which is fine — verifier no-ops.
FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]]; then
    # No file_path → not an Edit/Write we can verify. Don't block.
    exit 0
fi

# Only .vue files are subject to per-file ui-* enforcement.
case "$FILE_PATH" in
    *.vue) ;;
    *) exit 0 ;;
esac

exec python3 "$GUARDRAILS_DIR/trtc_verify_ui.py" --file "$FILE_PATH"
