$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path "F:\github\ziwei-network-analyst\work" | Out-Null
$out = "F:\github\ziwei-network-analyst\work\dump-real.out"
$err = "F:\github\ziwei-network-analyst\work\dump-real.err"
$meta = "F:\github\ziwei-network-analyst\work\dump-real.meta"
Remove-Item $out,$err,$meta -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "npm.cmd" -ArgumentList @("exec","--yes","--","tsx@4.19.4","scripts/dump-for-network-analyst.ts") -WorkingDirectory "F:\github\ziwei-doushu" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id)" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 420 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"
$n = 0
if (Test-Path "F:\github\ziwei-network-analyst\fixtures\real-1990") {
  $n = (Get-ChildItem "F:\github\ziwei-network-analyst\fixtures\real-1990\*.json" -File).Count
}
Add-Content -LiteralPath $meta -Value "files=$n"