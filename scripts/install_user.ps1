[CmdletBinding()]
param(
    [string]$RepoUrl = "https://github.com/Di0105/envi-mcp-server.git",
    [string]$InstallDir = "$env:USERPROFILE\envi-mcp-server",
    [switch]$SkipClone,
    [switch]$SkipVSCodeRegistration,
    [switch]$SkipConnectivityCheck
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Install-FromZip {
    param(
        [string]$ZipUrl,
        [string]$TargetDir
    )
    $zipPath = Join-Path $env:TEMP "envi-mcp-server-main.zip"
    $extractDir = Join-Path $env:TEMP "envi-mcp-server-main"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    Write-Step "Downloading $ZipUrl"
    Invoke-WebRequest $ZipUrl -OutFile $zipPath
    Expand-Archive $zipPath -DestinationPath $extractDir -Force
    $sourceDir = Join-Path $extractDir "envi-mcp-server-main"
    if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
    Move-Item $sourceDir $TargetDir
}

Write-Step "Checking prerequisites"
Require-Command py

if (-not $SkipClone) {
    if (-not (Test-Path $InstallDir)) {
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Step "Cloning $RepoUrl to $InstallDir"
            git clone $RepoUrl $InstallDir
            if ($LASTEXITCODE -ne 0) {
                Write-Step "git clone failed; falling back to ZIP download"
                Install-FromZip "https://github.com/Di0105/envi-mcp-server/archive/refs/heads/main.zip" $InstallDir
            }
        } else {
            Write-Step "Git not found; falling back to ZIP download"
            Install-FromZip "https://github.com/Di0105/envi-mcp-server/archive/refs/heads/main.zip" $InstallDir
        }
    } else {
        Write-Step "Using existing install directory $InstallDir"
    }
}

if (-not (Test-Path (Join-Path $InstallDir "pyproject.toml"))) {
    throw "InstallDir does not look like envi-mcp-server: $InstallDir"
}

Set-Location $InstallDir
$python = Join-Path $InstallDir ".venv312\Scripts\python.exe"

Write-Step "Creating Python 3.12 virtual environment"
py -3.12 -m venv .venv312

Write-Step "Installing ENVI/SARScape MCP server"
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[mcp]"

if (-not $SkipConnectivityCheck) {
    Write-Step "Running ENVI/SARScape connectivity check"
    & $python scripts/check_connectivity.py --json connectivity_report_py312.json
}

if (-not $SkipVSCodeRegistration) {
    Write-Step "Registering VS Code user MCP server and agent"
    & $python scripts/register_vscode_agent.py --repo-root $InstallDir --python $python
}

Write-Step "Done"
Write-Host "MCP Python: $python"
Write-Host "Repo root:  $InstallDir"