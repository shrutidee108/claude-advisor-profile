# .claude-advisor-profile

Canonical source for Maha's **advisor** Claude Code profile. Cloned on both the
Mac Studio and the Video computer (Windows 11, Tailscale-meshed). Repo location
is unconstrained — the launcher detects its own path at startup and patches
`${REPO_DIR}` placeholders in the settings file before passing it to Claude
Code, so any clone path works (`~/.claude-advisor-profile`, `D:\projects\...`,
wherever).

## What lives here

```
.claude-advisor-profile/
├── cc-advisor                  # Mac/Linux launcher (bash)
├── cc-advisor.ps1              # Windows launcher (PowerShell)
├── settings.json               # Mac/Linux settings — uses ${REPO_DIR} placeholder
├── settings-windows.json       # Windows settings — uses ${REPO_DIR} placeholder + py invocation
├── hooks/
│   ├── advisor-guard.py        # PreToolUse: allowlist + pre-read secret scan (true blocker)
│   ├── advisor-kill-phrase.py  # UserPromptSubmit: halts turn on "STOP STOP STOP"
│   └── advisor-exfil-guard.py  # PostToolUse: audit-only secret detection log
└── skills/
    └── advisor-mode/SKILL.md   # "I advise; I do not execute" system prompt
```

## Why this exists

Per the Sumantra-replacement plan (`~/.claude/plans/first-of-all-i-fancy-bachman.md`),
Phase 0 stands up a bare-bones Claude Code surface with **architectural** tool-gating.
The advisor physically cannot call `Bash`, `Write`, `Edit`, `NotebookEdit`, or
`WebFetch`. Specialist work is delegated — either interactively via skill invocation
or (Phase 3 onward) via the mission-control dispatcher.

This replaces prose-based delegation (ClaudeClaw's `CLAUDE.md` told Sumantra to
"coordinate, don't do" — that dissolved under load; seven cursing incidents in
April 2026 mapped to Sumantra doing specialist work in-turn).

## Setup (one-time, per machine)

```bash
git clone https://github.com/shrutidee108/claude-advisor-profile.git <wherever>
```

That's it for hooks/settings. Then copy the `advisor-mode` skill once so Claude
Code's skill discovery picks it up:

**Mac/Linux:**
```bash
mkdir -p ~/.claude/skills/advisor-mode
cp <wherever>/skills/advisor-mode/SKILL.md ~/.claude/skills/advisor-mode/
```

**Windows (PowerShell):**
```powershell
$dst = "$HOME\.claude\skills\advisor-mode"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "<wherever>\skills\advisor-mode\SKILL.md" $dst -Force
```

Re-run the copy line after any `git pull` that touches the SKILL.md.

## Launching the advisor

**Mac/Linux:**
```bash
<wherever>/cc-advisor
<wherever>/cc-advisor -p "your prompt"   # one-shot print mode
```

**Windows:**
```powershell
<wherever>\cc-advisor.ps1
<wherever>\cc-advisor.ps1 -p "your prompt"
```

The launcher detects its own location, substitutes `${REPO_DIR}` in the
settings file, and passes the patched JSON inline to `claude --settings`.

## Updating

```bash
cd <wherever>
git commit -am "advisor: <what changed>"
git push
# on the other machine
git pull
```

No CC restart needed — settings are re-read on each session start. The
launcher re-substitutes paths every launch.

## Notes

- The canonical plan file (`~/.claude/plans/first-of-all-i-fancy-bachman.md`)
  still shows hook filenames with `.sh` extensions. The 2026-04-24 handoff
  supersedes that: hooks are **Python** for cross-platform reach.
- Hooks read tool-call JSON from stdin and either exit 2 to block or print a
  JSON allow-response and exit 0. See `advisor-guard.py` for the contract.
- Kill-phrase default is `"STOP STOP STOP"` (override via `ADVISOR_KILL_PHRASE`).
- Secret-detection patterns are ported from
  `/Users/shrutidee/claudeclaw/src/exfiltration-guard.ts`.
- **Security model (verified 2026-04-25):** real prevention happens in
  `advisor-guard.py` (PreToolUse) — it reads the target file before `Read`
  executes, scans for secrets, and blocks the Read entirely if any match.
  Blocked file bytes never enter the model's context. The PostToolUse
  `advisor-exfil-guard.py` is an audit-only detector — Claude Code's
  PostToolUse hooks cannot redact non-MCP tool_results; the hook fires
  alongside the result, but the result itself still reaches the model.
  Phase 0.6 follow-up: use `updatedMCPToolOutput` in the PostToolUse
  hook to redact MCP tool returns specifically.
