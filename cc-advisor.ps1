# cc-advisor.ps1 — launch the advisor profile on Windows.
#
# Usage:
#   .\cc-advisor.ps1                    # interactive session
#   .\cc-advisor.ps1 -p "your prompt"   # one-shot print mode
#   .\cc-advisor.ps1 -p "..." -- ...    # any other flags pass through
#
# What it does: invokes `claude` with --settings pointing at the Windows-side
# settings file in this repo, and --setting-sources user so project/local
# settings can't leak permissive allowlists into the advisor session.

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$settings = Join-Path $repoDir 'settings-windows.json'

if (-not (Test-Path $settings)) {
    Write-Error "settings-windows.json not found at $settings"
    exit 1
}

# Pass all arguments through to claude
& claude --settings $settings --setting-sources user @args
exit $LASTEXITCODE
