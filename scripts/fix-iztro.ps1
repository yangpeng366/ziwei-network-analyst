$ErrorActionPreference = "Continue"
# stop leftover npm
Get-Process -Id 25908 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Set-Location "F:\github\ziwei-doushu"
Remove-Item ".\node_modules\iztro" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\node_modules\lunar-lite" -Recurse -Force -ErrorAction SilentlyContinue
$meta = "F:\github\ziwei-network-analyst\work\npm-iztro.meta"
$out = "F:\github\ziwei-network-analyst\work\npm-iztro.out"
$err = "F:\github\ziwei-network-analyst\work\npm-iztro.err"
Remove-Item $meta,$out,$err -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "npm.cmd" -ArgumentList @("install","iztro@2.5.8","lunar-javascript@1.7.3","--registry","https://registry.npmmirror.com","--no-fund","--no-audit","--prefer-offline=false") -WorkingDirectory "F:\github\ziwei-doushu" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id) clean-reinstall" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 300 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"
Add-Content -LiteralPath $meta -Value ("iztro_utils=" + (Test-Path ".\node_modules\iztro\lib\utils"))
Add-Content -LiteralPath $meta -Value ("iztro_index=" + (Test-Path ".\node_modules\iztro\lib\index.js"))