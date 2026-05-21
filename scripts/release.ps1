#Requires -Version 7
<#
.SYNOPSIS
    Build and publish a SnipLingo release.

.DESCRIPTION
    Automates the mechanical release steps:
      1. Sets the version in pyproject.toml and src/sniplingo/__init__.py
      2. Runs the ruff + pytest gate
      3. Builds the one-folder exe with PyInstaller and zips it
      4. Commits the version bump (if changed), then creates and pushes tag vX.Y.Z
      5. Creates the GitHub release and uploads the zip

    The parts a script cannot do (deciding the version, writing the release
    notes, authenticating `gh`) are covered by the `release` skill
    (.claude/skills/release/SKILL.md).

.PARAMETER Version
    Release version WITHOUT the leading 'v', e.g. 0.2.0

.PARAMETER NotesFile
    Path to a markdown file with the release notes (you write this — see
    scripts/RELEASE_NOTES_TEMPLATE.md). It becomes the GitHub release body.

.PARAMETER SkipTests
    Skip the ruff + pytest gate (not recommended).

.PARAMETER DryRun
    Do everything locally (version, build, zip, commit, tag) but do NOT push
    or create the GitHub release.

.EXAMPLE
    pwsh scripts/release.ps1 -Version 0.2.0 -NotesFile notes-0.2.0.md

.EXAMPLE
    pwsh scripts/release.ps1 -Version 0.2.0 -NotesFile notes-0.2.0.md -DryRun
#>
param(
    [Parameter(Mandatory)][string]$Version,
    [Parameter(Mandatory)][string]$NotesFile,
    [switch]$SkipTests,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $Exe $($Arguments -join ' ')"
    }
}

function Resolve-Tool {
    param([string]$Name, [string[]]$Fallbacks)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($f in $Fallbacks) { if (Test-Path $f) { return $f } }
    throw "$Name not found. Install it or add it to PATH."
}

function Set-FileVersion {
    param([string]$Path, [string]$Pattern, [string]$Replacement)
    $content = [System.IO.File]::ReadAllText($Path)
    $updated = [regex]::Replace($content, $Pattern, $Replacement)
    [System.IO.File]::WriteAllText($Path, $updated, [System.Text.UTF8Encoding]::new($false))
}

# --- locate repo root + tools ---------------------------------------------------
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "venv python not found at $py (run: pip install -e `".[dev]`")." }

$git = Resolve-Tool 'git' @('C:\Program Files\Git\cmd\git.exe')
$gh = Resolve-Tool 'gh' @('C:\Program Files\GitHub CLI\gh.exe')
# `gh` shells out to git, so make sure git's directory is on PATH for this process.
$env:PATH = (Split-Path $git) + ';' + $env:PATH

# --- validate inputs ------------------------------------------------------------
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must be X.Y.Z (got '$Version')." }
$NotesFile = (Resolve-Path $NotesFile).Path  # throws if missing
$tag = "v$Version"

$existingTags = & $git tag --list
if ($existingTags -contains $tag) {
    throw "Tag $tag already exists. Bump the version, or remove it: git tag -d $tag ; git push origin :refs/tags/$tag"
}

Write-Host "==> Releasing SnipLingo $tag" -ForegroundColor Cyan

# --- 1. set version -------------------------------------------------------------
Set-FileVersion (Join-Path $root 'pyproject.toml') '(?m)^version = ".*"$' "version = `"$Version`""
Set-FileVersion (Join-Path $root 'src\sniplingo\__init__.py') '__version__ = ".*"' "__version__ = `"$Version`""

# --- 2. gate: ruff + tests ------------------------------------------------------
if (-not $SkipTests) {
    Write-Host "==> ruff + pytest" -ForegroundColor Cyan
    Invoke-Native $py @('-m', 'ruff', 'check', '.')
    Invoke-Native $py @('-m', 'ruff', 'format', '--check', '.')
    Invoke-Native $py @('-m', 'pytest', '-q')
}

# --- 3. build + package ---------------------------------------------------------
Write-Host "==> Building exe" -ForegroundColor Cyan
Get-Process SnipLingo -ErrorAction SilentlyContinue | Stop-Process -Force
$dist = Join-Path $root 'dist'
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
Invoke-Native $py @('-m', 'PyInstaller', 'sniplingo.spec', '--noconfirm', '--clean')

$zip = Join-Path $dist "SnipLingo-$Version-win64.zip"
Compress-Archive -Path (Join-Path $dist 'SnipLingo') -DestinationPath $zip -Force
Write-Host "    packaged: $zip"

# --- 4. commit (only the version bump, if changed) + tag ------------------------
Invoke-Native $git @('add', 'pyproject.toml', 'src/sniplingo/__init__.py')
$staged = & $git diff --cached --name-only
if ($staged) { Invoke-Native $git @('commit', '-m', "Release $tag") }
else { Write-Host "    version already $Version; nothing to commit" }
Invoke-Native $git @('tag', '-a', $tag, '-m', "SnipLingo $tag")

if ($DryRun) {
    Write-Host "==> DryRun: skipped push + GitHub release. Tag $tag created locally." -ForegroundColor Yellow
    Write-Host "    Undo tag: git tag -d $tag" -ForegroundColor Yellow
    return
}

# --- 5. push + GitHub release ---------------------------------------------------
Write-Host "==> Pushing + creating GitHub release" -ForegroundColor Cyan
Invoke-Native $git @('push')
Invoke-Native $git @('push', 'origin', $tag)
Invoke-Native $gh @('release', 'create', $tag, $zip, '--title', "SnipLingo $Version", '--notes-file', $NotesFile)

Write-Host "==> Done: https://github.com/racode246/sniplingo/releases/tag/$tag" -ForegroundColor Green
