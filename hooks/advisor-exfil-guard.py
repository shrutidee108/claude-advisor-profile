#!/usr/bin/env python3
"""
advisor-exfil-guard.py — PostToolUse hook for the advisor profile.

**AUDIT LOG, NOT A BLOCKER.** Scans tool results for leaked secrets and logs
matches. Empirically (and per the docs as of 2026-04-25), Claude Code's
PostToolUse hook with exit 2 *cannot* redact tool_result content for
non-MCP tools — the original tool_result still reaches the model context
along with the hook's stderr message. So the meaningful prevention happens
at PreToolUse via advisor-guard.py's pre-read scan; this hook is a
detection/audit layer for cases that slip past (notably MCP tool returns,
where `updatedMCPToolOutput` could in principle redact — Phase 0.6 follow-up).

Patterns are a Python port of scanForSecrets() + redactSecrets() from
/Users/shrutidee/claudeclaw/src/exfiltration-guard.ts:
  anthropic_key, generic_sk_key, slack_token, github_token, aws_key, hex_key,
  plus optional env_value scanning against $ADVISOR_PROTECTED_VALUES.

Contract (Claude Code hooks):
  - stdin:  JSON {tool_name, tool_input, tool_response, session_id, ...}
  - exit 2: surface stderr to the model as feedback; tool_result still flows
  - exit 0: pass through silently

Fail-open on our own errors (never break the session because the guard itself
crashed — loud log, quiet pass-through).
"""

import base64
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "advisor-exfil-guard.log"

# ── Detection patterns (order matters: anthropic_key before generic_sk_key) ──
PATTERNS = [
    ("anthropic_key",   re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("generic_sk_key",  re.compile(r"sk-(?!ant-)[A-Za-z0-9_-]{20,}")),
    ("slack_token",     re.compile(r"xox[bp]-[A-Za-z0-9-]+")),
    ("github_token",    re.compile(r"gh[po]_[A-Za-z0-9]{20,}")),
    ("aws_key",         re.compile(r"AKIA[A-Za-z0-9]{16}")),
    # 41+ hex chars (unambiguously not a git SHA, which is exactly 40 chars)
    ("hex_key_long",    re.compile(r"(?<![A-Za-z0-9])[0-9a-fA-F]{41,}(?![A-Za-z0-9])")),
]

# Exactly 40 hex chars — could be a git SHA. Only flag if no git prefix precedes it.
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
                "position": m.start(),
                "length": len(m.group(0)),
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
            "position": m.start(),
            "length": len(m.group(0)),
            "preview": m.group(0)[:8] + "...",
        })

    if protected_values:
        for value in protected_values:
            if len(value) <= 8:
                continue
            variants = [
                ("base64",      base64.b64encode(value.encode()).decode()),
                ("url_encoded", urllib.parse.quote(value)),
            ]
            for label, encoded in variants:
                if label == "url_encoded" and encoded == value:
                    continue
                start = 0
                while True:
                    idx = text.find(encoded, start)
                    if idx == -1:
                        break
                    key = f"{idx}:{len(encoded)}"
                    if key not in seen:
                        seen.add(key)
                        matches.append({
                            "type": f"env_value_{label}",
                            "position": idx,
                            "length": len(encoded),
                            "preview": encoded[:8] + "...",
                        })
                    start = idx + 1

    matches.sort(key=lambda m: m["position"])
    return matches


def stringify_tool_response(response) -> str:
    """Tool responses can be dicts, lists, or strings. Flatten to a single string
    for pattern scanning."""
    if isinstance(response, str):
        return response
    try:
        return json.dumps(response, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(response)


def log_event(payload: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Fail open — don't break the session over a parser error.
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    response = data.get("tool_response", "")
    text = stringify_tool_response(response)

    protected = os.environ.get("ADVISOR_PROTECTED_VALUES", "")
    protected_list = [v for v in protected.split(",") if v] if protected else None

    try:
        matches = scan_for_secrets(text, protected_list)
    except re.error:
        sys.exit(0)

    if not matches:
        sys.exit(0)

    # Secrets detected. Log and block. We log pattern types + previews only,
    # never full matches — this log itself must not become an exfil channel.
    log_event({
        "ts": datetime.now().isoformat(),
        "session_id": data.get("session_id", ""),
        "tool_name": tool_name,
        "match_count": len(matches),
        "match_types": sorted({m["type"] for m in matches}),
        "previews": [m["preview"] for m in matches][:20],
    })

    summary = ", ".join(f"{m['type']}={m['preview']}" for m in matches[:5])
    print(
        "ADVISOR EXFIL GUARD: tool result contained "
        f"{len(matches)} potential secret match(es) ({summary}). "
        "Result discarded before it reached the advisor. "
        f"See {LOG_PATH} for the audit entry.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
