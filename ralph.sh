#!/bin/bash
# ralph.sh — Master orchestrator
# Stop:   Ctrl+C
# Resume: ./ralph.sh (picks up from first unchecked task)

NTFY_TOPIC="your-random-topic-here"  # e.g. ralph-x7k2m9pq — treat as a password
LOG_FILE="ralph.log"

# ── Notifications: ntfy (phone) with macOS fallback ──────────────────────
notify() {
  if curl -s -o /dev/null -w "%{http_code}" \
    -d "$1" "https://ntfy.sh/$NTFY_TOPIC" | grep -q "^200$"; then
    return
  fi
  osascript -e "display notification \"$1\" with title \"Ralph 🤖\"" 2>/dev/null || true
}

# ── Timestamped log ───────────────────────────────────────────────────────
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# ── Pre-flight checks ─────────────────────────────────────────────────────
if [ ! -f TASKS.md ]; then
  echo "❌ No TASKS.md found. Run ./plan.sh first."; exit 1
fi

if [ ! -f ralph-task.sh ]; then
  echo "❌ ralph-task.sh not found."; exit 1
fi

# Require a clean build baseline before starting
if ! npm run build > /dev/null 2>&1; then
  echo "❌ Project does not build cleanly. Fix errors first: npm run build"
  exit 1
fi

# ── Start ─────────────────────────────────────────────────────────────────
START_TIME=$(date +%s)
TASK_COUNT=0

echo ""
log "🚀 Ralph starting"
notify "Ralph started 🚀"

# ── Main loop ─────────────────────────────────────────────────────────────
while true; do
  NEXT=$(grep -m 1 "^- \[ \]" TASKS.md)

  if [ -z "$NEXT" ]; then
    ELAPSED=$(( ($(date +%s) - START_TIME) / 60 ))
    echo ""
    echo "🎉 All tasks complete!"
    log "🎉 Done — $TASK_COUNT tasks in ${ELAPSED} minutes"
    notify "🎉 All done! $TASK_COUNT tasks in ${ELAPSED}min"
    exit 0
  fi

  TASK=$(echo "$NEXT" | sed 's/^- \[ \] //')
  TASK_COUNT=$((TASK_COUNT + 1))
  TASK_START=$(date +%s)

  echo ""
  echo "========================================="
  log "📌 Task $TASK_COUNT: $TASK"
  echo "========================================="

  ./ralph-task.sh "$TASK"

  if [ $? -eq 0 ]; then
    TASK_ELAPSED=$(( $(date +%s) - TASK_START ))

    # Mark complete — awk handles special chars (/, [], () etc.) in task names
    awk -v task="$TASK" \
      '{if (!done && $0 == "- [ ] " task) {print "- [x] " task; done=1} else print}' \
      TASKS.md > TASKS.md.tmp && mv TASKS.md.tmp TASKS.md

    # Stage and safety-check commit size before pushing
    git add .
    FILE_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')

    if [ "$FILE_COUNT" -gt 100 ]; then
      git reset HEAD . 2>/dev/null
      log "⚠️  Large commit ($FILE_COUNT files) on task $TASK_COUNT — stopping"
      notify "⚠️ $FILE_COUNT files staged — check .gitignore"
      echo "Fix .gitignore, then re-run ./ralph.sh"
      exit 1
    fi

    git commit -m "feat: $TASK"

    # Fail loudly on push failure — silent failures are invisible overnight
    git push || {
      log "⚠️  Push failed on task $TASK_COUNT"
      notify "⚠️ Push failed on task $TASK_COUNT — check network/auth"
      exit 1
    }

    log "✅ Task $TASK_COUNT done in ${TASK_ELAPSED}s: $TASK"
    notify "✅ ($TASK_COUNT) Done in ${TASK_ELAPSED}s: $TASK"
    sleep 2

  else
    log "🛑 Stuck on task $TASK_COUNT: $TASK"
    notify "🛑 Stuck on task $TASK_COUNT — needs you"
    echo ""
    echo "Fix manually if needed, then re-run ./ralph.sh"
    exit 1
  fi
done