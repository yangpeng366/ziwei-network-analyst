$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
$dir = "$RepoRoot\fixtures\real-1990"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue | Remove-Item -Force
Start-Process pwsh -ArgumentList @("-NoProfile","-File","$RepoRoot\scripts\run-dump-real.ps1") -WindowStyle Hidden
Write-Output "cleared and relaunched"