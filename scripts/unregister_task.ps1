param(
  [string]$TaskName = 'MarketBriefingUpdateEvery30Min'
)

$ErrorActionPreference = 'Stop'

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Unregistered scheduled task: $TaskName"
