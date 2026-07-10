$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Worker = Join-Path $Root "tools\paper_qualification_worker.py"
$Logs = Join-Path $Root "logs"

$Stdout = Join-Path $Logs "paper_worker.stdout.log"
$Stderr = Join-Path $Logs "paper_worker.stderr.log"
$Supervisor = Join-Path $Logs "paper_worker.supervisor.log"

New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Set-Location $Root

$env:PYTHONUNBUFFERED = "1"
$env:CYBERCORE_TIMEZONE = "America/Denver"

while ($true) {
    $Started = [DateTimeOffset]::UtcNow.ToString("o")

    Add-Content `
        -LiteralPath $Supervisor `
        -Value "$Started starting paper qualification worker"

    try {
        & $Python -u $Worker 1>> $Stdout 2>> $Stderr
        $ExitCode = $LASTEXITCODE
    }
    catch {
        $ExitCode = -1

        Add-Content `
            -LiteralPath $Stderr `
            -Value "$([DateTimeOffset]::UtcNow.ToString('o')) $($_.Exception.Message)"
    }

    Add-Content `
        -LiteralPath $Supervisor `
        -Value "$([DateTimeOffset]::UtcNow.ToString('o')) worker exited code=$ExitCode; restarting in 5 seconds"

    Start-Sleep -Seconds 5
}
