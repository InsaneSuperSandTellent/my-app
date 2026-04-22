#!/bin/bash
# ralph-task.sh — Inner loop: one task → build → retry with errors
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
⚠️  Previous attempt failed (last 80 lines of build output):
$(tail -80 "$BUILD_LOG")

Fix these specific errors. Do not rewrite working code — only fix what's broken."
  else
    ERRORS_CONTEXT=""
  fi

  claude --model claude-opus-4-7 claude---dangerously-skip-permissions --print "
You are building a production application. Complete this task precisely.

Task: $TASK
$ERRORS_CONTEXT

Rules:
- Read SPEC.md to understand requirements
- Read TASKS.md to understand what is already built — do not redo it
- Read existing source files before modifying them
- Make minimal changes — only build what this task requires
- Do not break existing functionality
- Use TypeScript strictly — no 'any' types
- When done, output exactly: TASK_COMPLETE
"

  npm run build > "$BUILD_LOG" 2>&1
  BUILD_EXIT=$?

  if [ $BUILD_EXIT -eq 0 ]; then
    echo "  ✅ Build passed on attempt $loop"
    rm -f "$BUILD_LOG"
    exit 0
  fi

  echo "  ❌ Build failed on attempt $loop"
  loop=$((loop + 1))
  sleep 2
done

echo "  🛑 Max retries ($MAX_LOOPS) reached — needs human review"

# Clean up partial/broken changes so ralph.sh exits on a clean state
git checkout . 2>/dev/null

rm -f "$BUILD_LOG"
exit 1