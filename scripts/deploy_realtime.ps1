param()

Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $root) { $root = Get-Location }
Set-Location $root

$venvPython = Join-Path $root "..\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error ".venv Python not found at $venvPython. Please create or activate the virtual environment first."
    exit 1
}

if (-not $env:CIS_DASHBOARD_SECRET) {
    $env:CIS_DASHBOARD_SECRET = "ci_test_secret_local_01234567890123456789"
    Write-Host "Set CIS_DASHBOARD_SECRET to a local test value"
}

$alertsFile = Join-Path $env:TEMP "cis_alerts.jsonl"
if (-not (Test-Path $alertsFile)) {
    New-Item -Path $alertsFile -ItemType File | Out-Null
}

Write-Host "Using Python: $venvPython"
Write-Host "Starting CIS main detector and portal..."

$mainJob = Start-Job -Name cis_main -ScriptBlock {
    param($py, $alerts)
    & $py -u -m cis.main_detector --alerts-file $alerts
} -ArgumentList $venvPython, $alertsFile

Start-Sleep -Seconds 1

$portalJob = Start-Job -Name cis_portal -ScriptBlock {
    param($py)
    & $py -u -m cis.run_portal
} -ArgumentList $venvPython

Write-Host "Started jobs: cis_main=$($mainJob.Id), cis_portal=$($portalJob.Id)"
Write-Host "Alert file: $alertsFile"
Write-Host "Use Get-Job to inspect jobs or Stop-Job to terminate them."
Write-Host "Tailing alerts file now..."

Get-Content -Path $alertsFile -Wait -Tail 0
