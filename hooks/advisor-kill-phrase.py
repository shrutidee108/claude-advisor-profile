#!/usr/bin/env python3
"""
advisor-kill-phrase.py — UserPromptSubmit hook for the advisor profile.

If the user types the kill-phrase, halt the turn immediately. This is Maha's
panic button — when the advisor is off the rails, a single paste-able string
stops it without having to mash Ctrl+C.

Contract (Claude Code hooks):
  - stdin:  JSON {prompt, session_id, ...}
  - exit 2: halt the turn (stderr message surfaces to user)
  - exit 0: continue normally

Default phrase: "STOP STOP STOP" (case-insensitive). Override via
ADVISOR_KILL_PHRASE env var if Maha wants a different trigger per machine.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PHRASE = "STOP STOP STOP"
LOG_PATH = Path.home() / ".claude" / "advisor-kill-phrase.log"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Malformed payload: don't halt on our own bug; just let it through.
        sys.exit(0)

    prompt = data.get("prompt", "") or ""
    phrase = os.environ.get("ADVISOR_KILL_PHRASE", DEFAULT_PHRASE)

    if phrase.lower() not in prompt.lower():
        sys.exit(0)

    # Log the trigger (best-effort; never block on log failure)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(json.dumps({
                "ts": datetime.now().isoformat(),
                "session_id": data.get("session_id", ""),
                "phrase": phrase,
            }) + "\n")
    except OSError:
        pass

    print(
        f"ADVISOR KILL PHRASE TRIGGERED ('{phrase}'): turn halted. "
        "Send a new prompt when ready.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
