# Video computer — step-by-step setup (Windows 11)

Walks you from "fresh PowerShell window on the Video computer" to "advisor
verified working" in ~15 minutes. Copy each block as-is — no edits needed.

> **Before you start:** Tailscale should be connected. You don't need admin or
> Developer Mode for any step here — the design avoids symlinks on Windows.

---

## Step 1 — Open PowerShell

Press `Win`, type `powershell`, press Enter. A regular (non-admin) PowerShell
window is fine.

---

## Step 2 — Prereqs precheck

Paste this block:

```powershell
Write-Host "=== Prereqs check ===" -ForegroundColor Cyan
$results = @()
foreach ($c in @(
    @{Name="git";    Cmd={ git    --version 2>$null }; Install="winget install --id Git.Git -e --source winget"},
    @{Name="python"; Cmd={ py -3   --version 2>$null }; Install="winget install --id Python.Python.3.13 -e --source winget"},
    @{Name="claude"; Cmd={ claude  --version 2>$null }; Install="npm install -g @anthropic-ai/claude-code"}
)) {
    $out = & $c.Cmd
    if ($out) { Write-Host ("  [OK]    {0,-7} {1}" -f $c.Name, $out) -ForegroundColor Green }
    else      { Write-Host ("  [MISS]  {0,-7} -> {1}" -f $c.Name, $c.Install) -ForegroundColor Yellow }
}
```

Output looks like:

```
[OK]    git     git version 2.45.1.windows.1
[OK]    python  Python 3.13.0
[MISS]  claude  -> npm install -g @anthropic-ai/claude-code
```

If everything is `[OK]`, jump to **Step 4**. If anything is `[MISS]`, do Step 3.

---

## Step 3 — Install missing prereqs

For each `[MISS]` row from Step 2, run the install command shown there. Examples:

```powershell
# git
winget install --id Git.Git -e --source winget

# python (only needed if MISS — installs Python 3.13 + py launcher)
winget install --id Python.Python.3.13 -e --source winget

# claude (requires Node.js — install via `winget install OpenJS.NodeJS` first if needed)
npm install -g @anthropic-ai/claude-code
```

After installs finish, **close PowerShell and reopen it** so the new tools land
on PATH. Re-run Step 2 to confirm everything is `[OK]`.

---

## Step 4 — Authenticate Claude

```powershell
claude auth status
```

If it says "not logged in," run `claude auth login` and follow the browser
prompt. Use the same Anthropic account you use on the Mac.

---

## Step 5 — Clone the advisor repo

```powershell
git clone https://github.com/shrutidee108/claude-advisor-profile.git $HOME\.claude-advisor-profile
Set-Location $HOME\.claude-advisor-profile
git log --oneline | Select-Object -First 3
```

Last line should show 3 short commit hashes — that means the clone worked.

---

## Step 6 — Install the advisor-mode skill

The hooks point at the cloned repo directly, so no symlinks are needed for
those. The `advisor-mode` SKILL.md is the one file Claude needs to find under
`~/.claude/skills/`. Copy it:

```powershell
$skillDst = "$HOME\.claude\skills\advisor-mode"
New-Item -ItemType Directory -Force -Path $skillDst | Out-Null
Copy-Item "$HOME\.claude-advisor-profile\skills\advisor-mode\SKILL.md" $skillDst -Force
Get-ChildItem $skillDst
```

Last command should list `SKILL.md` with a recent timestamp.

> **Re-copy after `git pull`:** if the SKILL.md changes upstream, re-run the
> three lines above.

---

## Step 7 — First launch (interactive)

```powershell
& $HOME\.claude-advisor-profile\cc-advisor.ps1
```

You should land in an interactive Claude session. The window header / status
should look normal. Type `/help` and verify the session starts. Then `Ctrl+D`
or `/exit` to leave.

---

## Step 8 — Smoke test (a) — Read works

```powershell
& $HOME\.claude-advisor-profile\cc-advisor.ps1 -p "Use Read on $HOME\.claude-advisor-profile\README.md and tell me how many lines it has. Just the number."
```

Expected: a line count between roughly 80 and 200, with no error output. This
confirms `settings-windows.json` loaded and `Read` is allowed.

---

## Step 9 — Smoke test (b) — Bash is blocked

```powershell
& $HOME\.claude-advisor-profile\cc-advisor.ps1 -p "Use the Bash tool to run 'dir'. Just invoke it, don't explain."
```

Expected: the response says Bash isn't available, OR the response contains the
text `ADVISOR GUARD: tool 'Bash' is not in the advisor's allowlist`. Either is
proof the deny list / guard hook is doing its job.

---

## Step 10 — Smoke test (c) — Kill phrase halts a turn

```powershell
& $HOME\.claude-advisor-profile\cc-advisor.ps1 -p "Tell me a joke. STOP STOP STOP"
```

Expected: empty or near-empty response. Then verify the log:

```powershell
Get-Content "$HOME\.claude\advisor-kill-phrase.log" -Tail 1
```

Should show a JSON line with today's date and `"phrase": "STOP STOP STOP"`.

---

## Step 11 — Smoke test (d) — Exfil guard blocks a fake secret

```powershell
'fake key sk-ant-fakefakefake-1234567890abcdefgh end' | Set-Content "$env:TEMP\advisor-exfil-test.txt"
& $HOME\.claude-advisor-profile\cc-advisor.ps1 -p "Read $env:TEMP\advisor-exfil-test.txt and echo back the contents verbatim."
```

Expected: the response says the exfil guard intercepted the read; the file's
contents are NOT echoed back. Verify the log:

```powershell
Get-Content "$HOME\.claude\advisor-exfil-guard.log" -Tail 1
```

Should show a JSON line with `"match_types":["anthropic_key"]` and a recent
timestamp.

---

## Step 12 — (Optional) Claude Desktop

This is the surface we ultimately want as primary, but the CLI above is the
verified path. Try the Desktop app once the CLI works.

1. Install: https://claude.ai/download
2. Sign in with the same Anthropic account.
3. Open Settings. Look for any of these (the menu has been changing):
   - "Profiles" → add one pointing at `$HOME\.claude-advisor-profile\settings-windows.json`
   - "Custom settings file" / "Workspace settings"
   - "MCP & Hooks"
4. If you find a settings-file option, point it at the file above and restart
   the app.
5. Test plan-view sidebar: open `~\.claude\plans\first-of-all-i-fancy-bachman.md`
   in the Desktop app and see if a side panel renders the markdown.
6. Test split-view: try opening a second session in the same project window.

If steps 3–6 don't have UI for it (or the UI behaves differently than expected),
**that's a finding** — write down what you saw and we'll adapt. The CLI path
is sufficient for Phase 0 sign-off.

---

## Step 13 — Report back

Run this and paste the output to the chat:

```powershell
Write-Host "=== SMOKE TEST SUMMARY ===" -ForegroundColor Cyan
Write-Host "Repo:";        Set-Location $HOME\.claude-advisor-profile; git log --oneline | Select-Object -First 3
Write-Host "`nSkill:";     Get-ChildItem "$HOME\.claude\skills\advisor-mode" -EA SilentlyContinue
Write-Host "`nKill log:";  Get-Content  "$HOME\.claude\advisor-kill-phrase.log" -Tail 1 -EA SilentlyContinue
Write-Host "`nExfil log:"; Get-Content  "$HOME\.claude\advisor-exfil-guard.log" -Tail 1 -EA SilentlyContinue
Write-Host "`nDesktop:    <write what you saw in step 12>"
```

Phase 0 sign-off requires Steps 8, 9, 10, 11 all behaving as described. Step 12
is bonus / discovery — partial findings are fine.

---

## If something breaks

- **Step 7 hangs or errors**: try `claude --settings $HOME\.claude-advisor-profile\settings-windows.json --setting-sources user --debug` and look at the stderr for which hook/path failed.
- **Hook commands fail with "py not found"**: rerun Step 2; if `py` is missing, install Python via Step 3.
- **`claude` not found after install**: Node global bin needs to be on PATH. Run `npm config get prefix` and add `<that path>\bin` to your user PATH (System → Advanced → Environment Variables).
- **Symlinks issue**: there shouldn't be any. If `Get-ChildItem $HOME\.claude\skills\advisor-mode` shows a `SymbolicLink` instead of a regular file, something went sideways — delete the dir and re-run Step 6.

For anything else, paste the error to the chat with which step you were on.
