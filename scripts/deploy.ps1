# deploy.ps1 - sync this repo's skill files to ~/.claude/skills so Claude Code loads them.
# The repo is the source of truth; ~/.claude/skills is a deployed copy.
# (A directory junction would avoid copying, but is blocked while the skill dir is in use;
#  copy-deploy is the robust fallback. Re-run this after editing the skill.)
$ErrorActionPreference = 'Stop'
$repo   = Split-Path -Parent $PSScriptRoot
$deploy = Join-Path $env:USERPROFILE '.claude\skills\adversarial-interview'
foreach ($d in @('scripts','templates','reference')) {
  New-Item -ItemType Directory -Force -Path (Join-Path $deploy $d) | Out-Null
}
Copy-Item (Join-Path $repo 'SKILL.md')      $deploy -Force
Copy-Item (Join-Path $repo 'scripts\*')     (Join-Path $deploy 'scripts')   -Force -Exclude '__pycache__','deploy.ps1'
Copy-Item (Join-Path $repo 'templates\*')   (Join-Path $deploy 'templates') -Force
Copy-Item (Join-Path $repo 'reference\*')   (Join-Path $deploy 'reference') -Force
Write-Output ("deployed skill -> " + $deploy)
