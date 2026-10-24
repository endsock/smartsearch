# Install the latest CLI build artifact to the local runtime directory.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File install_win.ps1 [-Target D:\GreenSoft\smart-search]
#
# Behavior:
#   1. Resolve the latest build from .desktop-artifacts/cli-manifest.json
#      (fallback: newest backend-* directory containing dist\smart-search).
#   2. Delete everything under the target directory.
#   3. Copy the build bundle into the target directory.
param(
    [string]$Target = "D:\GreenSoft\smart-search"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ArtifactsRoot = Join-Path $RepoRoot ".desktop-artifacts"
$ManifestPath = Join-Path $ArtifactsRoot "cli-manifest.json"

# --- Resolve latest bundle -------------------------------------------------
$Bundle = $null
if (Test-Path $ManifestPath) {
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    if ($manifest.bundle_directory -and (Test-Path $manifest.bundle_directory)) {
        $Bundle = $manifest.bundle_directory
    }
}
if (-not $Bundle) {
    $candidate = Get-ChildItem -Path $ArtifactsRoot -Directory -Filter "backend-*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName "dist\smart-search" } |
        Where-Object { Test-Path $_ } |
        Select-Object -First 1
    if (-not $candidate) {
        Write-Error "No build artifact found under $ArtifactsRoot. Run scripts\build-cli.ps1 first."
        exit 1
    }
    $Bundle = $candidate
}

$Executable = Join-Path $Bundle "smart-search.exe"
if (-not (Test-Path $Executable)) {
    Write-Error "Bundle found but $Executable is missing."
    exit 1
}
Write-Host "Bundle     : $Bundle"

# --- Wipe target -----------------------------------------------------------
if (Test-Path $Target) {
    Write-Host "Clearing   : $Target"
    Remove-Item -Path (Join-Path $Target "*") -Recurse -Force
} else {
    Write-Host "Creating   : $Target"
    New-Item -ItemType Directory -Path $Target | Out-Null
}

# --- Copy ------------------------------------------------------------------
Write-Host "Copying to   : $Target"
Copy-Item -Path (Join-Path $Bundle "*") -Destination $Target -Recurse -Force

$installed = Get-ChildItem -Path $Target -Recurse -File | Measure-Object
Write-Host ""
Write-Host "Install completed: $Target ($($installed.Count) files)"
Write-Host "Executable : $(Join-Path $Target 'smart-search.exe')"
