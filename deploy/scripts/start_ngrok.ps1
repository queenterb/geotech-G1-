param(
    [string]$AuthToken = $env:NGROK_AUTHTOKEN,
    [int]$Port = 8000
)

if (-not $AuthToken) {
    Write-Error "Missing ngrok auth token. Set NGROK_AUTHTOKEN or pass -AuthToken <token>."
    exit 1
}

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
    Write-Error "ngrok executable not found in PATH. Install ngrok and ensure it is available."
    exit 2
}

Write-Host "Configuring ngrok authtoken..."
& $ngrok.Source config add-authtoken $AuthToken
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to configure ngrok authtoken."
    exit $LASTEXITCODE
}

Write-Host "Starting ngrok tunnel on port $Port..."
Start-Process -FilePath $ngrok.Source -ArgumentList "http", "$Port" -NoNewWindow
Write-Host "ngrok started. Use http://127.0.0.1:4040/api/tunnels to fetch the public URL."