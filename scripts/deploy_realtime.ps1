param()

# Realtime deploy script for Windows (PowerShell)
Set-StrictMode -Version Latest

# Ensure CIS secret
if (-not $env:CIS_DASHBOARD_SECRET) {
    $env:CIS_DASHBOARD_SECRET = "ci_test_secret_local_01234567890123456789"
    Write-Host "Set CIS_DASHBOARD_SECRET to a local test value"
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $root) { $root = Get-Location }
Set-Location $root

Write-Host "Installing Python dependencies (may take a moment)..."
python -m pip install --upgrade pip | Out-Null
python -m pip install -r cis/requirements.txt Flask pytest | Out-Null

# Alerts file
$alertsFile = Join-Path $env:TEMP "cis_alerts.jsonl"
if (-not (Test-Path $alertsFile)) { New-Item -Path $alertsFile -ItemType File | Out-Null }

Write-Host "Starting CIS main detector and portal..."

# Start main detector as a background job
Start-Job -Name cis_main -ScriptBlock {
    param($alertsFile)
    python -u -m cis.main_detector --alerts-file $alertsFile
} -ArgumentList $alertsFile | Out-Null

# Start portal (Flask) as a background job
Start-Job -Name cis_portal -ScriptBlock {
    python -u -m cis.run_portal
} | Out-Null

Write-Host "Services started. Tailing alerts file: $alertsFile"
Get-Content -Path $alertsFile -Wait -Tail 0
