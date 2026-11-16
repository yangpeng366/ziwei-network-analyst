# repo-paths.ps1 - single derivation point for repo root / engine root.
# Scripts must not hardcode drive letters or absolute paths.
#
# Usage (dot-source, so the variables land in the caller's scope):
#   . (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')    # this file lives in scripts\lib
#
# Yields:
#   $RepoRoot    repo root (= parent of scripts), so scripts work from any cwd
#   $EngineRoot  upstream chart engine ziwei-doushu: $env:ZIWEI_ENGINE_ROOT wins,
#                otherwise the sibling directory ..\ziwei-doushu
#   Assert-EngineRoot  fails with an actionable message when the engine is absent,
#                instead of letting tsx / npm run inside an empty directory
#
# Keep this file ASCII-only: Windows PowerShell 5.1 decodes a BOM-less .ps1 as ANSI,
# and non-ASCII text then breaks the parser. CONTRIBUTING also asks for UTF-8 without BOM.

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$EngineRoot = if ($env:ZIWEI_ENGINE_ROOT) {
    $env:ZIWEI_ENGINE_ROOT
} else {
    Join-Path (Split-Path -Parent $RepoRoot) 'ziwei-doushu'
}

function Assert-EngineRoot {
    if (-not (Test-Path (Join-Path $EngineRoot 'package.json'))) {
        throw "Upstream chart engine not found: $EngineRoot. Clone ziwei-doushu (see README) or set `$env:ZIWEI_ENGINE_ROOT to point at it."
    }
}
