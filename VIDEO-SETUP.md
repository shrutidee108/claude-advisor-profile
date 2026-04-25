# Video computer setup — Windows 11

Steps to bring up the advisor on the Video computer after the Mac side is ready.

## Prerequisites

- Tailscale installed and connected (you already have this).
- Git for Windows: https://git-scm.com/download/win
- Developer Mode enabled (Settings → Privacy & security → For developers →
  Developer Mode ON). This lets non-admin PowerShell create symlinks.
- Claude Desktop: https://claude.ai/download
- Claude Code CLI for Windows (fallback if Desktop misbehaves): `npm i -g
  @anthropic-ai/claude-code` (requires Node.js).

## Step 1 — Clone the advisor-profile repo

After we pick a remote (GitHub private / Gitea / something on Tailscale), in
PowerShell:

```powershell
git clone <remote-url> $HOME\.claude-advisor-profile
```

The repo must land at `$HOME\.claude-advisor-profile` specifically — the
hook paths inside `settings.json` assume that location on Windows.

## Step 2 — Fix hook paths for Windows

The committed `settings.json` hard-codes `/Users/shrutidee/.claude/hooks/*.py`
(Mac paths). On Windows, either:

**Option A — override via environment variable before launching Claude:**

```powershell
# Not currently wired; would require a small settings.json refactor. See
# Option B for Phase 0.
```

**Option B — local-only Windows settings override (Phase 0 recommended):**

Create `$HOME\.claude-advisor-profile-local\settings.json` with Windows paths:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher":"","hooks":[{"type":"command","command":"C:\\Users\\<you>\\.claude-advisor-profile\\hooks\\advisor-guard.py"}]}],
    "UserPromptSubmit": [{"matcher":"","hooks":[{"type":"command","command":"C:\\Users\\<you>\\.claude-advisor-profile\\hooks\\advisor-kill-phrase.py"}]}],
    "PostToolUse": [{"matcher":"","hooks":[{"type":"command","command":"C:\\Users\\<you>\\.claude-advisor-profile\\hooks\\advisor-exfil-guard.py"}]}]
  }
}
```

Launch Claude with both settings files merged:

```powershell
claude --settings "$HOME\.claude-advisor-profile\settings.json" `
       --settings "$HOME\.claude-advisor-profile-local\settings.json" `
       --setting-sources user
```

> **Note from Phase 0:** We should refactor `settings.json` to use `$HOME`-relative
> paths or environment-variable expansion so one file works on both platforms.
> Flagging for a Phase 0.5 follow-up — not a Phase 0 blocker.

## Step 3 — Python interpreter

The hooks are Python 3. Make sure `python3` resolves on the PATH, or edit each
hook's shebang line to point at `C:\Python313\python.exe` or similar. If you
installed Python via the official installer with "Add to PATH" checked, no
change needed.

Verify:

```powershell
python3 --version
# Should print something like: Python 3.12.x or Python 3.13.x
```

## Step 4 — Claude Desktop configuration

1. Open Claude Desktop.
2. Add the `yrf-paperclip` project folder (or whichever folder on Video you
   want to scope the advisor to).
3. Settings → Profiles (or equivalent) → point at
   `$HOME\.claude-advisor-profile\settings.json` as the settings file.
4. Verify plan-view sidebar opens and lists `~/.claude/plans/*.md`.
5. Verify split-view opens a second session.

## Step 5 — Smoke test

From the Claude Desktop advisor session (or from PowerShell running the CLI):

### (a) Bash denied

Prompt: `Use the Bash tool to run 'dir'. Don't explain — just invoke it.`

Expected: advisor refuses or reports that `Bash` is not available.

### (b) Read works

Prompt: `Use Read on C:\\Windows\\System32\\drivers\\etc\\hosts and tell me how many lines it has.`

Expected: advisor calls Read and reports a line count.

### (c) Kill phrase halts a turn

Prompt: `Tell me a joke. STOP STOP STOP`

Expected: no response text. Check `$HOME\.claude\advisor-kill-phrase.log`
(or wherever Windows puts it — adjust the LOG_PATH in the hook if needed) for a
log entry with the current timestamp.

### (d) Exfil guard blocks a secret

```powershell
Set-Content -Path $env:TEMP\advisor-exfil-test.txt -Value "fake key sk-ant-fakefakefake-1234567890abcdefgh end"
```

Prompt: `Read $env:TEMP\advisor-exfil-test.txt and echo back the contents.`

Expected: advisor reports the guard intercepted the read; file contents are NOT
echoed.

### (e) Plan-view renders

Open `~/.claude/plans/first-of-all-i-fancy-bachman.md` in the plan-view sidebar.
Verify the markdown renders and is scrollable.

### (f) Split-view works

Open a second session in the same project. Verify both sessions coexist and
have independent turn history.

## Step 6 — Report back

Once 5(a) through 5(f) all pass, tell Maha → Phase 0 is done and Phase 1 can
start. If any test fails, open a session in the Mac advisor profile and we'll
debug from there.
