#!/usr/bin/env python3
"""
advisor-guard.py — PreToolUse hook for the advisor profile.

Belt-and-suspenders layer on top of settings.json `permissions.deny`.
If a newly-added SDK tool ever leaks past the deny list (the deny list can't
match tools that don't exist yet), this hook catches it at harness level.

Contract (Claude Code hooks):
  - stdin:  JSON {tool_name, tool_input, session_id, ...}
  - exit 2: block the tool call (stderr message surfaces to user)
  - exit 0 + JSON {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "allow"}}: pass through

The advisor is read-only. Every tool call is classified either "advisory" (allow)
or "execution" (block). Unknown tools default to BLOCK (fail closed).
"""

import json
import sys

# Tools the advisor may use. Anything not in this set is denied at this layer
# regardless of what settings.json says.
ALLOWED_TOOLS = {
    # Core reads
    "Read", "Grep", "Glob",
    # Meta / session control
    "Skill", "ToolSearch", "AskUserQuestion",
    "EnterPlanMode", "ExitPlanMode",
    "TodoWrite", "TaskCreate", "TaskGet", "TaskList", "TaskOutput",
    "ScheduleWakeup",
    # Read-only web
    "WebSearch",
}

# Allowed MCP tool name *prefixes* — we namespace by server so a new read-only
# tool on a trusted server doesn't need a hook update to pass.
ALLOWED_MCP_PREFIXES = (
    "mcp__obsidian__read_",
    "mcp__obsidian__search_",
    "mcp__obsidian__list_",
    "mcp__obsidian__get_",
    "mcp__smart-connections__",
    "mcp__linear__get_",
    "mcp__linear__list_",
    "mcp__linear__search_",
    "mcp__jcodemunch__get_",
    "mcp__jcodemunch__list_",
    "mcp__jcodemunch__search_",
    "mcp__google-workspace__list",
    "mcp__google-workspace__read",
    "mcp__google-workspace__get",
    "mcp__google-workspace__search",
    "mcp__google-workspace__findElement",
)


def is_allowed(tool_name: str) -> bool:
    if tool_name in ALLOWED_TOOLS:
        return True
    for prefix in ALLOWED_MCP_PREFIXES:
        if tool_name.startswith(prefix):
            return True
    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # If we can't parse stdin, fail closed
        print("advisor-guard: could not parse hook payload; blocking", file=sys.stderr)
        sys.exit(2)

    tool_name = data.get("tool_name", "")

    if is_allowed(tool_name):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }))
        sys.exit(0)

    # Denied. Tell the advisor why so it switches to delegation instead of
    # retrying with a different argument shape.
    reason = (
        f"ADVISOR GUARD: tool '{tool_name}' is not in the advisor's allowlist. "
        "The advisor is read-only: coordinate and delegate, do not execute. "
        "For execution work, describe the step and hand off to mission-control "
        "(Phase 3) or invoke a skill that dispatches a fresh subprocess."
    )
    print(reason, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
