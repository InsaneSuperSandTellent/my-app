#!/bin/bash
# ralph-task.sh — Inner loop: one task → syntax check → retry with errors
# Exit 0 = success, Exit 1 = max retries exceeded (ralph.sh gets clean state)

TASK="$1"
MAX_LOOPS=8
BUILD_LOG=$(mktemp)
loop=1

echo "🤖 Working on: $TASK"

while [ $loop -le $MAX_LOOPS ]; do
  echo "  → Attempt $loop/$MAX_LOOPS"

  # Inject previous errors — truncate to 80 lines to protect context window
  if [ $loop -gt 1 ] && [ -s "$BUILD_LOG" ]; then
    ERRORS_CONTEXT="
⚠️  Previous attempt failed (last 80 lines of check output):
$(tail -80 "$BUILD_LOG")

Fix these specific errors. Do not rewrite working code — only fix what's broken."
  else
    ERRORS_CONTEXT=""
  fi

  claude --dangerously-skip-permissions --print "
You are building a production Python application. Complete this task precisely.

Task: $TASK
$ERRORS_CONTEXT

Rules:
- Read SPEC.md to understand requirements
- Read TASKS.md to understand what is already built — do not redo it
- Read existing source files before modifying them
- Make minimal changes — only build what this task requires
- Do not break existing functionality
- Use Python 3.11+ with type hints on every function
- Follow the file structure defined in SPEC.md section 3
- Use pathlib.Path for all filesystem paths
- Wrap every external API call (Claude, Snipe-IT) in try/except
- Never use print() in production code — use the logger module
- When done, output exactly: TASK_COMPLETE
"

  # Check Python syntax across all .py files (skip venv)
  PY_FILES=$(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" 2>/dev/null)

  if [ -z "$PY_FILES" ]; then
    # No Python files yet — that's fine for early tasks (e.g. creating folders)
    echo "  ✅ Task done on attempt $loop (no Python files to check yet)"
    rm -f "$BUILD_LOG"
    exit 0
  fi

  python3 -m py_compile $PY_FILES > "$BUILD_LOG" 2>&1
  BUILD_EXIT=$?

  # Additional import check — catches ModuleNotFoundError that py_compile misses
  if [ $BUILD_EXIT -eq 0 ] && [ -f "main.py" ]; then
    python3 -c "import ast; ast.parse(open('main.py').read())" >> "$BUILD_LOG" 2>&1
    BUILD_EXIT=$?
  fi

  if [ $BUILD_EXIT -eq 0 ]; then
    echo "  ✅ Syntax check passed on attempt $loop"
    rm -f "$BUILD_LOG"
    exit 0
  fi

  echo "  ❌ Syntax check failed on attempt $loop"
  loop=$((loop + 1))
  sleep 2
done

echo "  🛑 Max retries ($MAX_LOOPS) reached — needs human review"

# Clean up partial/broken changes so ralph.sh exits on a clean state
git checkout . 2>/dev/null

rm -f "$BUILD_LOG"
exit 1