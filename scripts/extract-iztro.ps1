$ErrorActionPreference = "Stop"
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
Expand-NpmTgz "F:\github\ziwei-network-analyst\work\iztro-2.5.8.tgz" "F:\github\ziwei-doushu\node_modules\iztro"
# deps often needed
npm pack lunar-lite --registry https://registry.npmmirror.com --pack-destination "F:\github\ziwei-network-analyst\work" | Out-Host
$lite = Get-ChildItem "F:\github\ziwei-network-analyst\work\lunar-lite-*.tgz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($lite) { Expand-NpmTgz $lite.FullName "F:\github\ziwei-doushu\node_modules\lunar-lite" }