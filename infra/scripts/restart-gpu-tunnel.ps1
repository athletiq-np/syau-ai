# PowerShell script to restart SSH tunnel to GPU server
# Usage: powershell -ExecutionPolicy Bypass -File restart-gpu-tunnel.ps1

$ErrorActionPreference = "SilentlyContinue"
$SSHHost = "ekduiteen@202.51.2.50"
$SSHPort = 41447
$LocalPort = 8188
$RemotePort = 8188
$LogFile = "$PSScriptRoot\tunnel.log"

function Log($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Add-Content $LogFile
    Write-Host "$timestamp - $message"
}

Log "=== Tunnel Restart Script Started ==="

# Kill existing SSH processes on the ports we're using
Log "Killing existing SSH processes on port $LocalPort..."
Get-Process ssh -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*8188*" -or $_.CommandLine -like "*8100*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

# Kill SSH processes more aggressively
Log "Force-stopping SSH processes..."
taskkill /F /IM ssh.exe 2>$null | Out-Null

Start-Sleep -Seconds 2

# Start new tunnel with exponential backoff
$maxRetries = 3
$retryCount = 0
$success = $false

while ($retryCount -lt $maxRetries -and -not $success) {
    $retryCount++
    Log "Tunnel connection attempt $retryCount of $maxRetries..."

    # Start SSH tunnel (non-blocking)
    $sshCmd = "ssh -N -L ${LocalPort}:localhost:${RemotePort} -p ${SSHPort} ${SSHHost}"
    Log "Executing: $sshCmd"

    try {
        # Start process in background
        $process = Start-Process -FilePath "ssh.exe" `
            -ArgumentList "-N -L ${LocalPort}:localhost:${RemotePort} -p ${SSHPort} ${SSHHost}" `
            -NoNewWindow `
            -PassThru `
            -ErrorAction Stop

        Log "SSH tunnel process started (PID: $($process.Id))"
        $success = $true

        # Wait a moment and check if process is still running
        Start-Sleep -Seconds 2
        if ($process.HasExited) {
            Log "WARNING: Process exited immediately"
            $success = $false
        }

    } catch {
        Log "ERROR: Failed to start SSH tunnel: $_"
        if ($retryCount -lt $maxRetries) {
            $waitTime = [Math]::Pow(2, $retryCount)
            Log "Waiting ${waitTime} seconds before retry..."
            Start-Sleep -Seconds $waitTime
        }
    }
}

if ($success) {
    Log "✓ Tunnel restart successful"
    exit 0
} else {
    Log "✗ Tunnel restart failed after $maxRetries attempts"
    exit 1
}
