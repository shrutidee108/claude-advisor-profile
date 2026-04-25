# cc-advisor.ps1 — launch the advisor profile on Windows.
#
# Detects its own location and substitutes ${REPO_DIR} in settings-windows.json
# (with double-backslash escaping for JSON), then passes the patched JSON
# inline to `claude --settings`. This means the repo can live anywhere — D:\,
# C:\Users\..., wherever — no hard-coded paths in committed files.
#
# Usage:
#   .\cc-advisor.ps1                    # interactive session
#   .\cc-advisor.ps1 -p "your prompt"   # one-shot print mode
#   .\cc-advisor.ps1 -p "..." ...       # any other flags pass through

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$settingsFile = Join-Path $repoDir 'settings-windows.json'

if (-not (Test-Path $settingsFile)) {
    Write-Error "settings-windows.json not found at $settingsFile"
    exit 1
}

# Read the canonical settings, substitute ${REPO_DIR} with the absolute path.
# Backslashes inside JSON strings need to be doubled, so substitute with the
# escaped form.
$settingsJson = Get-Content -Raw $settingsFile
$repoDirJson = $repoDir -replace '\\', '\\'
$patched = $settingsJson.Replace('${REPO_DIR}', $repoDirJson)

& claude --settings $patched --setting-sources user @args
exit $LASTEXITCODE
