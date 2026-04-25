#!/usr/bin/env python3
"""
advisor-guard.py — PreToolUse hook for the advisor profile.

Two responsibilities:

1. **Allowlist enforcement.** Belt-and-suspenders on top of settings.json
   `permissions.deny`. If a newly-added SDK tool ever leaks past the deny list
   (the deny list can't match tools that don't exist yet), this catches it.

2. **Pre-read secret scan.** Before a `Read` tool executes, the hook reads the
   target file itself, scans it with the same regex set as the exfil-guard, and
   BLOCKS the Read entirely if any secret pattern matches. This is the only
   architecturally-sound way to prevent secrets from entering the model's
   context: PostToolUse hooks cannot redact non-MCP tool results in current
   Claude Code (verified empirically + via docs lookup 2026-04-25). The
   PostToolUse exfil-guard is now an audit log, not a blocker.

Contract (Claude Code hooks):
  - stdin:  JSON {tool_name, tool_input, session_id, ...}
  - exit 2: block the tool call (stderr message surfaces to user)
  - exit 0 + JSON {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "allow"}}: pass through

Unknown tools default to BLOCK (fail closed). Read calls whose target file is
unreadable (permission, not found) pass through to let CC surface its own
error — we don't second-guess CC on file-system errors.
"""

import base64
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Allowlist ────────────────────────────────────────────────────────────────

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


# ── Pre-read secret scan ────────────────────────────────────────────────────

LOG_PATH = Path.home() / ".claude" / "advisor-guard.log"

# Cap how much we read into the scan — full file would blow up on large logs.
# 4 MiB is well above any reasonable text file we'd Read interactively.
MAX_SCAN_BYTES = 4 * 1024 * 1024

PATTERNS = [
    ("anthropic_key",   re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("generic_sk_key",  re.compile(r"sk-(?!ant-)[A-Za-z0-9_-]{20,}")),
    ("slack_token",     re.compile(r"xox[bp]-[A-Za-z0-9-]+")),
    ("github_token",    re.compile(r"gh[po]_[A-Za-z0-9]{20,}")),
    ("aws_key",         re.compile(r"AKIA[A-Za-z0-9]{16}")),
    ("hex_key_long",    re.compile(r"(?<![A-Za-z0-9])[0-9a-fA-F]{41,}(?![A-Za-z0-9])")),
]

HEX40 = re.compile(r"(?<![A-Za-z0-9])[0-9a-fA-F]{40}(?![A-Za-z0-9])")
GIT_SHA_PREFIX = re.compile(r"(?:commit |tree |parent |object |[0-9a-f]{40}\.\.)")


def scan_for_secrets(text: str, protected_values: list[str] | None = None) -> list[dict]:
    matches: list[dict] = []
    seen: set[str] = set()

    for type_, regex in PATTERNS:
        for m in regex.finditer(text):
            key = f"{m.start()}:{len(m.group(0))}"
            if key in seen:
                continue
            seen.add(key)
            matches.append({
                "type": type_,
                "preview": m.group(0)[:8] + "...",
            })

    for m in HEX40.finditer(text):
        if len(m.group(0)) != 40:
            continue
        prefix = text[max(0, m.start() - 10): m.start()]
        if GIT_SHA_PREFIX.search(prefix):
            continue
        key = f"{m.start()}:{len(m.group(0))}"
        if key in seen:
            continue
        seen.add(key)
        matches.append({
            "type": "hex_key_40",
            "preview": m.group(0)[:8] + "...",
        })

    if protected_values:
        for value in protected_values:
            if len(value) <= 8:
                continue
            for label, encoded in (
                ("base64",      base64.b64encode(value.encode()).decode()),
                ("url_encoded", urllib.parse.quote(value)),
            ):
                if label == "url_encoded" and encoded == value:
                    continue
                if encoded in text:
                    matches.append({
                        "type": f"env_value_{label}",
                        "preview": encoded[:8] + "...",
                    })
    return matches


def log_event(payload: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def scan_read_target(file_path: str, session_id: str) -> str | None:
    """Scan the file the model is about to Read. Return a block-reason string
    if the file contains secrets, or None if it's clean / unreadable."""
    if not file_path:
        return None
    try:
        with open(file_path, "rb") as f:
            raw = f.read(MAX_SCAN_BYTES)
    except (OSError, IOError):
        # Don't second-guess CC on FS errors — let CC's own Read surface the error
        return None
    text = raw.decode("utf-8", errors="replace")

    protected = os.environ.get("ADVISOR_PROTECTED_VALUES", "")
    protected_list = [v for v in protected.split(",") if v] if protected else None

    try:
        matches = scan_for_secrets(text, protected_list)
    except re.error:
        return None
    if not matches:
        return None

    log_event({
        "ts": datetime.now().isoformat(),
        "session_id": session_id,
        "file_path": file_path,
        "match_count": len(matches),
        "match_types": sorted({m["type"] for m in matches}),
        "previews": [m["preview"] for m in matches][:20],
    })
    summary = ", ".join(f"{m['type']}={m['preview']}" for m in matches[:5])
    return (
        f"ADVISOR PRE-READ SCAN: file '{file_path}' contains "
        f"{len(matches)} potential secret match(es) ({summary}). "
        "Read blocked at PreToolUse — the file's contents never entered the "
        f"model's context. See {LOG_PATH} for the audit entry. "
        "If this is a legitimate read of a config file with embedded secrets, "
        "ask Maha to read it himself and paste the relevant lines."
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("advisor-guard: could not parse hook payload; blocking", file=sys.stderr)
        sys.exit(2)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    # Step 1 — allowlist
    if not is_allowed(tool_name):
        print(
            f"ADVISOR GUARD: tool '{tool_name}' is not in the advisor's allowlist. "
            "The advisor is read-only: coordinate and delegate, do not execute. "
            "For execution work, describe the step and hand off to mission-control "
            "(Phase 3) or invoke a skill that dispatches a fresh subprocess.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Step 2 — pre-read secret scan (Read only; other tools have their own limits)
    if tool_name == "Read":
        block = scan_read_target(
            tool_input.get("file_path", ""),
            data.get("session_id", ""),
        )
        if block:
            print(block, file=sys.stderr)
            sys.exit(2)

    # Allow
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
