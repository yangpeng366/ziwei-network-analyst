$ErrorActionPreference = "Stop"
Set-Location "F:\github\ziwei-doushu"
Write-Host "npm install iztro lunar-javascript tsx"
npm install iztro@2.5.8 lunar-javascript@1.7.3 tsx@4.19.0 --no-save --no-package-lock
if ($LASTEXITCODE -ne 0) { throw "npm failed" }
Write-Host "ok"
Test-Path ".\node_modules\iztro"
Test-Path ".\node_modules\tsx"