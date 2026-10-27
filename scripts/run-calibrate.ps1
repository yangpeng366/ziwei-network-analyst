$ErrorActionPreference = "Continue"
$out = "F:\github\ziwei-network-analyst\work\calibrate.out"
$err = "F:\github\ziwei-network-analyst\work\calibrate.err"
$meta = "F:\github\ziwei-network-analyst\work\calibrate.meta"
Remove-Item $out,$err,$meta -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "python" -ArgumentList @("F:\github\ziwei-network-analyst\scripts\calibrate-real-1990.py") -WorkingDirectory "F:\github\ziwei-network-analyst" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id)" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 300 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"