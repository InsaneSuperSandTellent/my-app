#!/bin/bash
# plan.sh — Generate TASKS.md from SPEC.md
# Archives previous versions automatically. Run once before ralph.sh.

if [ ! -f SPEC.md ]; then
  echo "❌ No SPEC.md found. Create your spec first."
  exit 1
fi

# Auto-increment version number for archiving
get_next_version() {
  local base=$1
  local ext=$2
  local v=1
  while [ -f "${base}-v${v}.${ext}" ]; do
    v=$((v + 1))
  done
  echo $v
}

# Archive TASKS.md
if [ -f TASKS.md ]; then
  V=$(get_next_version "TASKS" "md")
  mv TASKS.md "TASKS-v${V}.md"
  echo "📦 Archived TASKS.md → TASKS-v${V}.md"
fi

# Archive SPEC.md
if [ -f SPEC.md ]; then
  V=$(get_next_version "SPEC" "md")
  mv SPEC.md "SPEC-v${V}.md"
  echo "📦 Archived SPEC.md → SPEC-v${V}.md"
fi

LATEST_SPEC=$(ls SPEC-v*.md 2>/dev/null | sort -V | tail -1)
LATEST_TASKS=$(ls TASKS-v*.md 2>/dev/null | sort -V | tail -1)

PRIOR_TASKS_CONTEXT=""
if [ -n "$LATEST_TASKS" ]; then
  PRIOR_TASKS_CONTEXT="
Also read ${LATEST_TASKS} — it contains all previously completed tasks.
Do NOT recreate work already done. Number new tasks continuing from the last number."
fi

echo "📋 Reading spec and generating task list..."

claude --dangerously-skip-permissions --print "
Read ${LATEST_SPEC} carefully. This is the full specification for what needs to be built.
${PRIOR_TASKS_CONTEXT}

Rules:
- Each task must be completable in one focused coding session
- Tasks in logical build order: foundation first, features next, polish last
- Each task independently testable with: npm run build
- Be specific — name the exact files and components involved
- Aim for 20-25 tasks total
- If prior tasks exist, number new ones continuing from the last number
- If fresh project, start at 001

Output ONLY this markdown format — no explanation, no preamble:

# Task List
- [x] 001: existing completed task (if prior tasks exist, keep unchanged)
- [ ] 002: [short name] | [one sentence: what to build and in which file]

Write directly to TASKS.md
"

echo ""
echo "✅ TASKS.md generated. Review before running ralph.sh:"
echo ""
cat TASKS.md

git add .
git commit -m "chore: archive v${V} specs, generate new TASKS.md" 2>/dev/null || true

echo ""
echo "📝 Edit TASKS.md if needed, then run: ./ralph.sh"