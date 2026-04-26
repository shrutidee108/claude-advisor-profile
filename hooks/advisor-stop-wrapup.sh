#!/usr/bin/env bash
# advisor-stop-wrapup.sh — Stop hook for the advisor profile.
#
# Fires when an advisor session ends. Spawns a DETACHED `claude -p /wrap-up`
# subprocess against the user's PRODUCTION (default) profile so the wrap-up
# skill can actually write to learnings.md files. The advisor itself is
# read-only by Phase 0 design (deny Bash/Write/Edit), so wrap-up cannot run
# in-session.
#
# Contract (Claude Code hooks):
#   - stdin:  JSON Stop event payload (we don't need to parse it for v1)
#   - exit 0: continue (must exit fast — hook runs synchronously at shutdown)
#
# Detachment:
#   - `nohup ... &` + `disown` so the child survives the parent (the advisor
#     `claude` process) exiting and is reparented to init/launchd.
#   - stdin from /dev/null, stdout+stderr discarded — child is fully headless.
#   - We do NOT pass --settings, so the spawned child reads the user's default
#     profile (production), not the advisor profile.
#
# Logging:
#   - One line per spawn to logs/wrapup-spawns.log: ISO-ts PID=<pid> reason
#   - Best-effort; never block on log failure.

set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LOG_DIR="$REPO_DIR/logs"
LOG_FILE="$LOG_DIR/wrapup-spawns.log"

# Drain stdin so the parent doesn't get SIGPIPE if it tries to write more.
# We don't need the payload for v1.
cat >/dev/null 2>&1 || true

# Ensure log dir exists (best-effort).
mkdir -p "$LOG_DIR" 2>/dev/null || true

# Spawn the wrap-up subprocess fully detached.
# - nohup: ignore SIGHUP when parent dies
# - </dev/null: no stdin (otherwise it might block waiting for input)
# - >/dev/null 2>&1: discard output (we're headless)
# - &: background
# - disown: detach from this shell's job table so it survives shell exit
# NOTE: claude has no --skill flag; the convention is to pass the slash
# command as the prompt. `/wrap-up` resolves to skills/wrap-up/SKILL.md
# in the user's default profile.
nohup claude -p "/wrap-up" </dev/null >/dev/null 2>&1 &
child_pid=$!
disown "$child_pid" 2>/dev/null || true

# Log the spawn (best-effort; never block).
{
    printf '%sT%s PID=%d advisor-session-end\n' \
        "$(date -u +%Y-%m-%d)" \
        "$(date -u +%H:%M:%S)" \
        "$child_pid" \
        >>"$LOG_FILE"
} 2>/dev/null || true

# Exit immediately so advisor shutdown isn't blocked.
exit 0
