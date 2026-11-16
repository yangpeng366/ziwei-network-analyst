$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
Assert-EngineRoot
New-Item -ItemType Directory -Force -Path "$RepoRoot\work" | Out-Null
$out = "$RepoRoot\work\dump-real.out"
$err = "$RepoRoot\work\dump-real.err"
$meta = "$RepoRoot\work\dump-real.meta"
Remove-Item $out,$err,$meta -Force -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "npm.cmd" -ArgumentList @("exec","--yes","--","tsx@4.19.4","scripts/dump-for-network-analyst.ts") -WorkingDirectory "$EngineRoot" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Set-Content -LiteralPath $meta -Value "pid=$($p.Id)" -Encoding utf8
try { Wait-Process -Id $p.Id -Timeout 420 } catch { Add-Content -LiteralPath $meta -Value "timeout" }
Add-Content -LiteralPath $meta -Value "exit=$($p.ExitCode) hasExited=$($p.HasExited)"
$n = 0
if (Test-Path "$RepoRoot\fixtures\real-1990") {
  $n = (Get-ChildItem "$RepoRoot\fixtures\real-1990\*.json" -File).Count
}
Add-Content -LiteralPath $meta -Value "files=$n"