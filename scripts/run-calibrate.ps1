$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
$out = "$RepoRoot\work\calibrate.out"
$err = "$RepoRoot\work\calibrate.err"
$meta = "$RepoRoot\work\calibrate.meta"
Remove-Item $out,$err,$meta -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "python" -ArgumentList @("$RepoRoot\scripts\calibrate-real-1990.py") -WorkingDirectory "$RepoRoot" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id)" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 300 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"