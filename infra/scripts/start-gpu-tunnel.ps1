param(
    [string]$HostName = "202.51.2.50",
    [int]$Port = 41447,
    [string]$User = "ekduiteen",
    [int]$LocalPort = 8100,
    [int]$RemotePort = 8100
)

$sshTarget = "$User@$HostName"
$forward = "$LocalPort`:127.0.0.1`:$RemotePort"

Write-Host "Opening SSH tunnel: localhost:$LocalPort -> $sshTarget:127.0.0.1:$RemotePort"
Write-Host "Keep this window open while testing remote inference."

ssh -p $Port -L $forward $sshTarget
