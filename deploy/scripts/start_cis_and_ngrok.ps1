param(
    [string]$AuthToken = $env:NGROK_AUTHTOKEN,
    [int]$Port = 8000,
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

function Get-NgrokTunnels {
    try {
        return Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 3
    } catch {
        return $null
    }
}

function Wait-ForCondition {
    param(
        [ScriptBlock]$Condition,
        [int]$Attempts = 60,
        [int]$DelaySeconds = 1,
        [string]$WaitingMessage = "Waiting..."
    )

    for ($i = 0; $i -lt $Attempts; $i++) {
        if (& $Condition) {
            return $true
        }
        Write-Host "$WaitingMessage ($($i + 1)/$Attempts)"
        Start-Sleep -Seconds $DelaySeconds
    }
    return $false
}

if (-not $AuthToken) {
    Write-Error "Missing ngrok auth token. Set NGROK_AUTHTOKEN or pass -AuthToken <token>."
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python executable not found: $PythonExe. Run this from the repository root or set -PythonExe to the correct path."
    exit 2
}

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
    Write-Error "ngrok executable not found in PATH. Install ngrok and ensure it is available."
    exit 3
}

$existingNgrok = Get-Process -Name ngrok -ErrorAction SilentlyContinue
if ($existingNgrok) {
    Write-Host "Stopping existing ngrok process(es)..."
    $existingNgrok | Stop-Process -Force
}

Write-Host "Configuring ngrok authtoken..."
& $ngrok.Source config add-authtoken $AuthToken
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to configure ngrok authtoken."
    exit $LASTEXITCODE
}

$cisProc = $null
if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet)) {
    Write-Host "Starting CIS service with $PythonExe..."
    $cisProc = Start-Process -FilePath $PythonExe -ArgumentList '-m', 'cis.service' -WorkingDirectory (Get-Location) -NoNewWindow -PassThru
} else {
    Write-Host "CIS service already listening on port $Port. Reusing existing service."
}

Write-Host "Waiting for CIS service to listen on port $Port..."
$ready = Wait-ForCondition -Condition { Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet } -Attempts 60 -DelaySeconds 1 -WaitingMessage "Waiting for local CIS service"
if (-not $ready) {
    Write-Error "CIS service did not start listening on port $Port within 60 seconds. Check the CIS service logs and try again."
    exit 4
}

Write-Host "Probing local health endpoint..."
$healthReady = Wait-ForCondition -Condition {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 3 -UseBasicParsing
        return $resp.StatusCode -eq 200
    } catch {
        return $false
    }
} -Attempts 30 -DelaySeconds 1 -WaitingMessage "Waiting for /healthz"

if (-not $healthReady) {
    Write-Warning "Local CIS service is listening but /healthz did not return 200 within 30 seconds."
}

Write-Host "Starting ngrok tunnel on port $Port..."
$ngrokStdout = Join-Path (Get-Location) 'ngrok_stdout.log'
$ngrokStderr = Join-Path (Get-Location) 'ngrok_stderr.log'
if (Test-Path $ngrokStdout) { Remove-Item $ngrokStdout -Force }
if (Test-Path $ngrokStderr) { Remove-Item $ngrokStderr -Force }
$ngrokProc = Start-Process -FilePath $ngrok.Source -ArgumentList 'http', "$Port", '--log=stdout', '--log-level=info' -WindowStyle Hidden -RedirectStandardOutput $ngrokStdout -RedirectStandardError $ngrokStderr -PassThru

Write-Host "Waiting for ngrok local API on 127.0.0.1:4040..."
$apiReady = Wait-ForCondition -Condition {
    Test-NetConnection -ComputerName 127.0.0.1 -Port 4040 -InformationLevel Quiet
} -Attempts 30 -DelaySeconds 1 -WaitingMessage "Waiting for ngrok API"
if (-not $apiReady) {
    Write-Error "ngrok local API did not become available at http://127.0.0.1:4040 within 30 seconds."
    Write-Host "ngrok logs:"; Get-Content $ngrokStdout -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { Write-Host $_ }
    Write-Host "ngrok stderr:"; Get-Content $ngrokStderr -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { Write-Host $_ }
    exit 6
}

Write-Host "Waiting for ngrok tunnel to become active..."
$publicUrl = $null
$ready = Wait-ForCondition -Condition {
    $tunnels = Get-NgrokTunnels
    if ($tunnels -and $tunnels.tunnels -and $tunnels.tunnels.Count -gt 0) {
        $publicUrl = $tunnels.tunnels[0].public_url
        return $true
    }
    return $false
} -Attempts 60 -DelaySeconds 1 -WaitingMessage "Waiting for ngrok public URL"

if (-not $ready -or -not $publicUrl) {
    Write-Warning "ngrok started, but the public URL could not be read from the local API. The tunnel may still be starting."
    Write-Host "Check http://127.0.0.1:4040/api/tunnels for status."
    Write-Host "ngrok logs:"; Get-Content $ngrokStdout -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { Write-Host $_ }
    Write-Host "ngrok stderr:"; Get-Content $ngrokStderr -ErrorAction SilentlyContinue | Select-Object -Last 40 | ForEach-Object { Write-Host $_ }
    exit 5
}

if ($cisProc) {
    Write-Host "CIS service PID: $($cisProc.Id)"
} else {
    Write-Host "CIS service already running on port $Port."
}
Write-Host "ngrok PID: $($ngrokProc.Id)"
Write-Host "Public URL: $publicUrl"
Write-Host "Open the URL above to reach the CIS app through ngrok."
Write-Host "Keep this PowerShell session open while the tunnel is active, or run the processes as a background task."
