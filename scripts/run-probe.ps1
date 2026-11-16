$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
Assert-EngineRoot
New-Item -ItemType Directory -Force -Path "$RepoRoot\work" | Out-Null
$out = "$RepoRoot\work\probe-chart.out"
$err = "$RepoRoot\work\probe-chart.err"
$meta = "$RepoRoot\work\probe-chart.meta"
Remove-Item $out,$err,$meta -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "npm.cmd" -ArgumentList @("exec","--yes","--","tsx@4.19.4","scripts/probe-chart.ts") -WorkingDirectory "$EngineRoot" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id)" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 240 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"