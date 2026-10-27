$ErrorActionPreference = "Stop"
$dest = "F:\github\ziwei-doushu\node_modules\lunar-typescript"
$tgz = "F:\github\ziwei-network-analyst\work\lunar-typescript-1.8.6.tgz"
$tmp = "F:\github\ziwei-network-analyst\work\lunar-typescript-extract"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
tar -xf $tgz -C $tmp
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Move-Item -LiteralPath (Join-Path $tmp "package") -Destination $dest
Write-Output ("pkg=" + (Test-Path (Join-Path $dest "package.json")))