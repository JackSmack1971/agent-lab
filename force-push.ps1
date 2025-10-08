<# 
.SYNOPSIS
  Initializes a Git repo (if needed), resets the remote "origin", and force-pushes local contents to GitHub.

.USAGE
  powershell -ExecutionPolicy Bypass -File .\force-push.ps1 `
    -RepoUrl "https://github.com/JackSmack1971/agent-lab.git" `
    -Branch "main" `
    -SkipConfirm

.PARAMETERS
  -RepoUrl     Remote origin URL (default: agent-lab repo).
  -Branch      Branch name to force-push (default: main).
  -SkipConfirm Skip the safety confirmation.
#>

[CmdletBinding()]
param(
  [string]$RepoUrl = "https://github.com/JackSmack1971/agent-lab.git",
  [string]$Branch = "main",
  [switch]$SkipConfirm
)

$ErrorActionPreference = "Stop"

function Assert-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

function Git-Configured {
  param([string]$Key)
  $val = ""
  try {
    $val = git config --get $Key 2>$null
  } catch { }
  return -not [string]::IsNullOrWhiteSpace($val)
}

try {
  Assert-Command -Name "git"

  # Show intent & confirm (unless skipped)
  Write-Host "Repository path: $(Resolve-Path .)"
  Write-Host "Remote URL     : $RepoUrl"
  Write-Host "Branch         : $Branch"
  Write-Host "Action         : FORCE push (remote will be overwritten)" -ForegroundColor Yellow

  if (-not $SkipConfirm) {
    $ans = Read-Host "Type 'OVERWRITE' to proceed"
    if ($ans -ne "OVERWRITE") {
      throw "Aborted by user."
    }
  }

  # Warn if Git identity missing (commits may fail)
  if (-not (Git-Configured "user.name") -or -not (Git-Configured "user.email")) {
    Write-Warning "Git user.name and/or user.email not set. If commit fails, set with:"
    Write-Warning "  git config user.name  ""Your Name"""
    Write-Warning "  git config user.email ""you@example.com"""
  }

  # Step 1: Initialize git if not already a repo
  if (-not (Test-Path -Path ".git")) {
    Write-Host "Initializing new Git repository..."
    git init | Out-Null
  } else {
    Write-Host "Existing Git repository detected."
  }

  Write-Host "Staging all files..."
  git add -A

  # Commit if there are staged changes
  $hasStagedChanges = $true
  try {
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { $hasStagedChanges = $false }
  } catch { }

  if ($hasStagedChanges) {
    Write-Host "Creating commit..."
    git commit -m "Initial commit - overwrite remote with local repo" | Out-Null
  } else {
    Write-Host "No staged changes to commit."
  }

  # Step 2: Reset remote origin
  $originExists = $false
  try {
    $originExists = git remote | Select-String -Pattern '^\s*origin\s*$' -Quiet
  } catch { $originExists = $false }

  if ($originExists) {
    Write-Host "Removing existing 'origin'..."
    git remote remove origin | Out-Null
  }

  Write-Host "Adding 'origin' -> $RepoUrl"
  git remote add origin $RepoUrl

  # Step 3: Force push to overwrite GitHub
  Write-Host "Setting primary branch to '$Branch'..."
  git branch -M $Branch

  Write-Host "Force-pushing to '$RepoUrl' ($Branch)..."
  git push -u origin $Branch --force

  Write-Host "`nDone. Remote '$Branch' now matches your local branch." -ForegroundColor Green
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
