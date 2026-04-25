# Handoff prompt — Video computer Claude Code session

You (Maha) do Steps 1–5 of `VIDEO-SETUP.md` yourself (open PowerShell, run the
prereqs precheck, install missing prereqs, `claude auth login`, `git clone` the
repo). Those steps need a human at the keyboard.

Once the clone is done, `cd $HOME\.claude-advisor-profile`, run `claude`, and
paste the prompt below. Claude Code on the Video machine will pick up Steps 6
through 13 and report back to you.

---

## Paste this verbatim:

```
You are running on Maha's Windows 11 "Video" computer in a fresh Claude Code
session. The current working directory is the freshly-cloned repo at
$HOME\.claude-advisor-profile. Your job is to execute Steps 6 through 13 of
VIDEO-SETUP.md and report the results.

Context (don't go researching this — accept it as given):
- This repo is the bare-bones "advisor" Claude Code profile per the YRF
  Sumantra-replacement plan. Phase 0 is bringing it up on this Video computer.
- The same profile is already verified working on Maha's Mac. Phase 0 sign-off
  for the Video side requires Steps 8, 9, 10, 11 to behave as described in
  VIDEO-SETUP.md. Step 12 is discovery (Claude Desktop UI may differ from the
  third-party YouTube summary the plan was based on); partial findings are fine.
- The advisor profile uses harness-level tool gating: a "deny list" in
  settings-windows.json plus three Python hooks in hooks/. The smoke tests
  prove these are wired up correctly on Windows.

Read VIDEO-SETUP.md in this directory, then execute Steps 6 through 13 in
order. Specifically:

1. Step 6: copy advisor-mode SKILL.md into $HOME\.claude\skills\advisor-mode\.
2. Step 7: launch cc-advisor.ps1 once interactively, confirm it starts, then
   exit. (This may not be feasible from inside an automated CC session — if you
   can't drive an interactive subprocess cleanly, skip Step 7 and tell Maha to
   spot-check it himself; do not block Steps 8–11 on it.)
3. Steps 8, 9, 10, 11: run each smoke test exactly as written in the doc. For
   each test, capture the command, the relevant tail of stdout, and the
   relevant log file (advisor-kill-phrase.log for Step 10, advisor-exfil-guard.log
   for Step 11). Determine PASS or FAIL based on the "Expected" line in the
   doc.
4. Step 12: open Claude Desktop, look for a Profiles or custom-settings option,
   and write down what UI you actually see. If you can't open Desktop apps
   from a CC session, tell Maha and skip — this is discovery, not a gate.
5. Step 13: produce the summary block exactly as the doc shows.

Operating constraints:

- Use TaskCreate to track Steps 6–13 as separate tasks. Mark each completed as
  you finish it; mark FAILED ones explicitly with the failure mode in the
  description.
- Ask Maha for permission before any command that mutates global state outside
  this repo (e.g., copying files into $HOME\.claude\, installing packages).
- Never run `--dangerously-skip-permissions` or similar. If a command needs
  approval, ask.
- If a smoke test fails, do NOT try to fix it on your own — capture the error
  output verbatim, mark the task FAILED, and continue to the next test. We'll
  diagnose failures together.
- The kill phrase for the advisor profile is "STOP STOP STOP" (case-insensitive).
  If during Step 7 or Step 12 the advisor session goes off-rails, paste the
  kill phrase to halt it.

When you're done, output:

1. A PASS/FAIL line for each of Steps 8, 9, 10, 11.
2. The Step 13 summary block in a code fence.
3. Whatever you found in Step 12 (or "skipped" if you couldn't drive the GUI).
4. Anything weird, unexpected, or worth flagging — be specific.

Begin.
```

---

## Notes for Maha (not for the Video CC)

- The handoff session above will run as a **regular full-permission CC**, not
  as the advisor. It needs Bash/Write to run the smoke tests, copy files, and
  inspect logs. Don't launch the advisor profile to drive this — the advisor
  is intentionally read-only.
- If the Video CC asks for approval on each command, that's fine — approve
  what you expect (file copies into `~/.claude/skills/`, reads, writes to
  `$env:TEMP`) and reject anything surprising.
- Step 7 (interactive launch) may not be drivable from an automated CC
  session. The handoff prompt tells CC to skip it gracefully if so. Worst
  case, you spot-check Step 7 yourself with one paste.
- Step 12 (Claude Desktop GUI) almost certainly can't be done from CC. The
  handoff prompt says so. You'll need to do this one yourself if you want it
  done — or defer it.
- Token cost: Steps 6, 8–11, 13 are short — this should be a cheap session
  (under 50k tokens).
