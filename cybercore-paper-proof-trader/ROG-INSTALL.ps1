$ErrorActionPreference = "Stop"

$Target = "C:\Users\eagle\code\worldmonitor\cybercore-paper-proof-trader"

if (-not (Test-Path $Target)) {
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
}

Copy-Item -Recurse -Force "$PSScriptRoot\*" $Target
Set-Location $Target

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".[test]"
& ".\.venv\Scripts\python.exe" -m pytest -q

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

& ".\.venv\Scripts\python.exe" -m cybercore_trader.cli init-data

Write-Host ""
Write-Host "Installed at $Target"
Write-Host "Set MORNING_APPROVAL_SIGNING_KEY in the process environment."
Write-Host "Set COINBASE_EXECUTOR_URL to the existing internal Coinbase order service."
Write-Host "Set COINBASE_TRADING_BALANCE_USD or wire a live balance provider."
Write-Host "Leave exchange keys inside the existing Coinbase executor."
