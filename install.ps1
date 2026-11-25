# agent-kit installer (Windows PowerShell). Preview by default; pass --apply to write.
# Usage: .\install.ps1 [--target DIR] [--skills-dir PATH] [--docs-dir PATH] [--no-guard] [--apply]
$ErrorActionPreference = "Stop"
$kitHome = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = $null
foreach ($name in @("py", "python", "python3")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { continue }
    $prefix = @()
    if ($name -eq "py") { $prefix = @("-3") }
    & $cmd.Source @prefix -c "import sys; sys.exit(sys.version_info < (3, 9))" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = @($cmd.Source) + $prefix; break }
}
if ($null -eq $python) {
    Write-Error "agent-kit: Python 3.9+ not found on PATH; nothing was installed."
    exit 2
}
$env:PYTHONPATH = $kitHome
$exe = $python[0]
$rest = @()
if ($python.Count -gt 1) { $rest = $python[1..($python.Count - 1)] }
& $exe @rest -m agentkit install @args
exit $LASTEXITCODE
