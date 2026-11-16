$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')
Assert-EngineRoot
function Expand-NpmTgz($tgz, $dest) {
  $tmp = "$dest-extract-tmp"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  tar -xf $tgz -C $tmp
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
  Move-Item -LiteralPath (Join-Path $tmp "package") -Destination $dest
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  Write-Output ("ok " + $dest + " utils=" + (Test-Path (Join-Path $dest "lib\utils\index.js")))
}
Expand-NpmTgz "$RepoRoot\work\iztro-2.5.8.tgz" "$EngineRoot\node_modules\iztro"
# deps often needed
npm pack lunar-lite --registry https://registry.npmmirror.com --pack-destination "$RepoRoot\work" | Out-Host
$lite = Get-ChildItem "$RepoRoot\work\lunar-lite-*.tgz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($lite) { Expand-NpmTgz $lite.FullName "$EngineRoot\node_modules\lunar-lite" }