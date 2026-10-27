$ErrorActionPreference = "Stop"
$outDir = "F:\github\ziwei-network-analyst\data\v4-sample"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zst = Join-Path $outDir "year-1990.jsonl.zst"
$url = "https://github.com/Renhuai123/ziwei-doushu/releases/download/v4.0-13d/year-1990.jsonl.zst"
if (Test-Path $zst) { Remove-Item -LiteralPath $zst -Force }
Write-Host "curl download start"
& curl.exe -L --retry 5 --retry-delay 2 --connect-timeout 30 -o $zst $url
if (-not (Test-Path $zst)) { throw "download missing" }
Write-Host ("size=" + (Get-Item -LiteralPath $zst).Length)
& zstd -t --long=27 $zst
if ($LASTEXITCODE -ne 0) { throw "zstd test failed" }
$jsonl = Join-Path $outDir "year-1990.jsonl"
& zstd -d --long=27 -f $zst -o $jsonl
Write-Host ("jsonl=" + (Get-Item -LiteralPath $jsonl).Length)