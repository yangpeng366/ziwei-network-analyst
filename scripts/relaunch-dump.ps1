$ErrorActionPreference = "Continue"
$dir = "F:\github\ziwei-network-analyst\fixtures\real-1990"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue | Remove-Item -Force
Start-Process pwsh -ArgumentList @("-NoProfile","-File","F:\github\ziwei-network-analyst\scripts\run-dump-real.ps1") -WindowStyle Hidden
Write-Output "cleared and relaunched"