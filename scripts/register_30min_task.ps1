param(
  [string]$TaskName = 'MarketBriefingUpdateEvery30Min',
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'

$updateScript = Join-Path $ProjectRoot 'scripts\update_market_briefing.ps1'
if (-not (Test-Path -LiteralPath $updateScript)) {
  throw "Update script not found: $updateScript"
}

$action = New-ScheduledTaskAction `
  -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$updateScript`" -ProjectRoot `"$ProjectRoot`""

$trigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).Date `
  -RepetitionInterval (New-TimeSpan -Minutes 30) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description 'Updates the market briefing webpage every 30 minutes.' `
  -Force

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runs every 30 minutes."
Write-Host "Update script: $updateScript"
