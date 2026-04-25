# .claude-advisor-profile

Canonical source for Maha's **advisor** Claude Code profile. Cloned on both the Mac
Studio and the Video computer (Windows 11, Tailscale-meshed); local `~/.claude/`
points into this repo via symlinks so profile changes flow through git instead of
hand-edits on each box.

## What lives here

```
.claude-advisor-profile/
├── settings.json                # --settings target; permissions.deny + hooks config
├── hooks/
│   ├── advisor-guard.py         # PreToolUse: harness-level denial of doing-tools
│   ├── advisor-kill-phrase.py   # UserPromptSubmit: halts turn on configured phrase
│   └── advisor-exfil-guard.py   # PostToolUse: redacts secrets before output leaves the agent
└── skills/
    ├── advisor-mode/SKILL.md    # "I advise; I do not execute" system prompt
    └── skill-router/SKILL.md    # Phase 4 — Haiku classifier that picks (skill_id, model)
```

## Why this exists

Per the Sumantra-replacement plan (`~/.claude/plans/first-of-all-i-fancy-bachman.md`),
Phase 0 stands up a bare-bones Claude Code surface with **architectural** tool-gating.
The advisor physically cannot call `Bash`, `Write`, `Edit`, `NotebookEdit`, or
`WebFetch`. Specialist work is delegated — either interactively via skill invocation
or (Phase 3 onward) via the mission-control dispatcher.

This replaces prose-based delegation (ClaudeClaw's `CLAUDE.md` told Sumantra to
"coordinate, don't do" — that dissolved under load; seven cursing incidents in April
2026 mapped to Sumantra doing specialist work in-turn).

## Launching the advisor

### Mac (bash/zsh)

```bash
claude --settings ~/.claude-advisor-profile/settings.json
```

A thin wrapper `cc-advisor` is added later in Phase 0 for convenience.

### Video computer (Windows 11, PowerShell)

```powershell
claude --settings $HOME\.claude-advisor-profile\settings.json
```

Primary surface on Video is the Claude Desktop app scoped to the yrf-paperclip
project folder; the CLI form above is the fallback.

## Setup (one-time, per machine)

```bash
git clone <remote> ~/.claude-advisor-profile

# symlinks from ~/.claude/ into this repo (Mac)
mkdir -p ~/.claude/profiles/advisor
ln -s ~/.claude-advisor-profile/settings.json ~/.claude/profiles/advisor/settings.json
ln -s ~/.claude-advisor-profile/hooks/advisor-guard.py       ~/.claude/hooks/advisor-guard.py
ln -s ~/.claude-advisor-profile/hooks/advisor-kill-phrase.py ~/.claude/hooks/advisor-kill-phrase.py
ln -s ~/.claude-advisor-profile/hooks/advisor-exfil-guard.py ~/.claude/hooks/advisor-exfil-guard.py
ln -s ~/.claude-advisor-profile/skills/advisor-mode  ~/.claude/skills/advisor-mode
ln -s ~/.claude-advisor-profile/skills/skill-router  ~/.claude/skills/skill-router
```

On Windows, use `mklink /D` in an elevated `cmd.exe` (PowerShell's `New-Item -ItemType
SymbolicLink` also works with admin rights or Developer Mode enabled).

## Updating

```bash
cd ~/.claude-advisor-profile
# edit files
git commit -am "advisor: <what changed>"
git push
# on the other machine
git pull
```

No CC restart needed — settings are re-read on each session start.

## Notes

- The canonical plan file (`~/.claude/plans/first-of-all-i-fancy-bachman.md`)
  still shows hook filenames with `.sh` extensions. The 2026-04-24 handoff
  supersedes that: hooks are **Python** for cross-platform reach (Mac + Windows).
- Hooks read tool-call JSON from stdin and either exit 2 to block or print a JSON
  allow-response and exit 0. See the `advisor-guard.py` docstring for the contract.
- Kill-phrase default is `"STOP STOP STOP"` (configurable in the hook file).
- Exfiltration patterns are ported from
  `/Users/shrutidee/claudeclaw/src/exfiltration-guard.ts`.
