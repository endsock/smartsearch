[CmdletBinding()]
param(
    [string] $PythonPath = "",
    [string] $OutputRoot = ".desktop-artifacts",
    [string] $ResultFile = ".desktop-artifacts/cli-manifest.json",
    [switch] $SkipInstall,
    [switch] $NoSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

function Resolve-Executable([string] $Candidate) {
    if ([System.IO.Path]::IsPathRooted($Candidate) -or $Candidate.Contains([System.IO.Path]::DirectorySeparatorChar) -or $Candidate.Contains('/')) {
        if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            throw "Python executable not found: $Candidate"
        }
        return [System.IO.Path]::GetFullPath($Candidate)
    }

    $command = Get-Command $Candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) {
        throw "Executable not found on PATH: $Candidate"
    }
    return $command.Source
}

function Resolve-RepositoryPath([string] $Candidate) {
    if ([System.IO.Path]::IsPathRooted($Candidate)) {
        return [System.IO.Path]::GetFullPath($Candidate)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $Candidate))
}

$venvPython = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if ($PythonPath) {
    $python = Resolve-Executable $PythonPath
} elseif (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $python = $venvPython
} else {
    $systemPython = Resolve-Executable "python"
    Write-Host "Creating build environment: $venvPython"
    & $systemPython -m venv (Split-Path -Parent $venvPython)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python virtual environment."
    }
    $python = $venvPython
}

$outputRoot = Resolve-RepositoryPath $OutputRoot
$resultFile = Resolve-RepositoryPath $ResultFile
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resultFile) | Out-Null

Push-Location $repositoryRoot
try {
    if (-not $SkipInstall) {
        Write-Host "Installing the current project and PyInstaller..."
        & $python -m pip install --disable-pip-version-check . "pyinstaller==6.22.3"
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed."
        }
    }

    $buildArguments = @(
        "desktop/scripts/build_backend.py",
        "--output-root", $outputRoot,
        "--result-file", $resultFile
    )
    if (-not $NoSmoke) {
        $buildArguments += "--smoke"
    }

    Write-Host "Building the PyInstaller onedir CLI backend..."
    & $python @buildArguments
    if ($LASTEXITCODE -ne 0) {
        throw "CLI backend build failed."
    }

    $manifest = Get-Content -Raw -LiteralPath $resultFile | ConvertFrom-Json
    Write-Host ""
    Write-Host "CLI backend build completed."
    Write-Host "Executable : $($manifest.executable)"
    Write-Host "Bundle     : $($manifest.bundle_directory)"
    Write-Host "Manifest   : $resultFile"
    if (-not $NoSmoke) {
        Write-Host "Smoke test : passed"
    }
} finally {
    Pop-Location
}
