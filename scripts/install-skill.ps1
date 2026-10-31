#!/usr/bin/env pwsh
# 安装仓内 Codex Skill 到全局 skills 目录。
#
# 为什么要有这个脚本：skill 装在 %USERPROFILE%\.codex-home\skills 下才会被
# 显式点名调用（`ziwei-network-analyst`）。改了仓内 skill 若不同步安装，
# 显式调用吃到的还是旧版——scripts/test-skill-entry.py 会报「全局 skill 与仓内不一致」。
#
# 用法：
#   pwsh -File scripts/install-skill.ps1
#   pwsh -File scripts/install-skill.ps1 -Dest D:\somewhere\ziwei-network-analyst
$ErrorActionPreference = 'Stop'

$src = Join-Path (Split-Path -Parent $PSScriptRoot) 'skill\ziwei-network-analyst'
if (-not (Test-Path -LiteralPath $src)) {
    throw "仓内 skill 不存在：$src"
}

$dest = if ($args.Count -ge 1 -and $args[0]) {
    $args[0]
} else {
    Join-Path $env:USERPROFILE '.codex-home\skills\ziwei-network-analyst'
}
$dest = [System.IO.Path]::GetFullPath($dest)
if ($dest.Split('\')[-1] -ne 'ziwei-network-analyst') {
    throw "目标目录名必须是 ziwei-network-analyst，实为：$dest"
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $src '*') -Destination $dest -Recurse -Force

$srcFiles = Get-ChildItem -LiteralPath $src -Recurse -File
$bad = @()
foreach ($f in $srcFiles) {
    $rel = $f.FullName.Substring($src.Length).TrimStart('\')
    $target = Join-Path $dest $rel
    if (-not (Test-Path -LiteralPath $target)) { $bad += "$rel（缺失）"; continue }
    if ((Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash) {
        $bad += "$rel（内容不一致）"
    }
}
if ($bad.Count -gt 0) {
    throw "安装校验失败：`n$($bad -join "`n")"
}
Write-Output "skill 已安装：$dest（$($srcFiles.Count) 个文件校验一致）"
