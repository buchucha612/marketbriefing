param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'

function Resolve-PythonExe {
  param([string]$Preferred)

  if ($Preferred -and (Test-Path -LiteralPath $Preferred)) {
    return $Preferred
  }

  $bundled = 'C:\Users\AHRIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (Test-Path -LiteralPath $bundled) {
    return $bundled
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return $python.Source
  }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return $py.Source
  }

  throw 'Python executable was not found.'
}

Set-Location -LiteralPath $ProjectRoot

$logDir = Join-Path $ProjectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir 'market_briefing_update.log'
$pythonPath = Resolve-PythonExe -Preferred $PythonExe

function Write-Log {
  param([string]$Message)
  $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Add-Content -LiteralPath $logPath -Encoding UTF8 -Value "[$timestamp] $Message"
}

function Invoke-Step {
  param(
    [string]$Name,
    [string[]]$Arguments
  )

  Write-Log "START $Name"
  & $pythonPath @Arguments 2>&1 | ForEach-Object {
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value $_
  }
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  Write-Log "DONE $Name"
}

try {
  Write-Log '===== market briefing update started ====='
  Write-Log "ProjectRoot=$ProjectRoot"
  Write-Log "Python=$pythonPath"

  Invoke-Step -Name 'collect news' -Arguments @('collectors/news.py')
  Invoke-Step -Name 'collect prices' -Arguments @('collectors/prices.py')
  Invoke-Step -Name 'build briefing' -Arguments @('processing/build_briefing.py')

  $outputDir = Join-Path $ProjectRoot 'outputs\market-briefing-mvp'
  New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

  $files = @(
    'index.html',
    'styles.css',
    'app.js',
    'briefing-data.js',
    'daily_market_briefing.json'
  )

  foreach ($file in $files) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "serving\$file") -Destination $outputDir -Force
  }

  Write-Log "Copied serving files to $outputDir"
  Write-Log '===== market briefing update completed ====='
}
catch {
  Write-Log "ERROR $($_.Exception.Message)"
  throw
}
