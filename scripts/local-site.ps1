param(
    [switch]$Stop,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Docker {
    param([string[]]$DockerArguments)
    # Windows PowerShell 5 treats redirected native stderr as error records.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $script:dockerCommand @DockerArguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "Docker exited with code $exitCode. See its output above."
    }
}

function Test-DockerReady {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $operatingSystem = & $script:dockerCommand info --format '{{.OSType}}' 2>$null
        return ($LASTEXITCODE -eq 0 -and $operatingSystem -eq 'linux')
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

try {
    $docker = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $docker) {
        throw 'Install Docker Desktop first: https://www.docker.com/products/docker-desktop/'
    }
    $script:dockerCommand = $docker.Source
    Invoke-Docker -DockerArguments @('compose', 'version')

    if (-not (Test-DockerReady)) {
        if ($Stop) {
            throw 'Docker is not running in Linux containers mode. Open Docker Desktop first.'
        }
        $desktopPaths = @(
            (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
            (Join-Path $env:LOCALAPPDATA 'Docker\Docker Desktop.exe')
        )
        $desktop = $desktopPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $desktop) {
            throw 'Open Docker Desktop in Linux containers mode, then run start-site.bat again.'
        }
        Write-Host 'Starting Docker Desktop. Waiting for the Linux engine...'
        Start-Process -FilePath $desktop
        $deadline = (Get-Date).AddSeconds(120)
        while (-not (Test-DockerReady)) {
            if ((Get-Date) -ge $deadline) {
                throw 'Docker did not become ready in 120 seconds. Check Docker Desktop / WSL, then retry.'
            }
            Start-Sleep -Seconds 2
        }
    }

    $composeArguments = @('compose', '--project-name', 'awanmarket', '--file',
        (Join-Path $projectRoot 'docker-compose.yml'))
    if ($Stop) {
        Invoke-Docker -DockerArguments ($composeArguments + @('stop'))
        Write-Host 'AwanMarket stopped. Your database is preserved.' -ForegroundColor Green
        exit 0
    }

    $envPath = Join-Path $projectRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) {
        $template = [System.IO.File]::ReadAllText((Join-Path $projectRoot '.env.example'))
        $randomBytes = New-Object byte[] 32
        $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $random.GetBytes($randomBytes) } finally { $random.Dispose() }
        $secret = [System.BitConverter]::ToString($randomBytes).Replace('-', '').ToLowerInvariant()
        $template = $template.Replace('replace-with-a-long-random-secret-at-least-32-characters', $secret)
        [System.IO.File]::WriteAllText($envPath, $template, (New-Object System.Text.UTF8Encoding $false))
        Write-Host 'Created .env. Administrator credentials are in that file.'
    }

    Write-Host 'Building and starting AwanMarket. The first launch can take several minutes...'
    Invoke-Docker -DockerArguments ($composeArguments + @('up', '--build', '--detach', '--wait', '--wait-timeout', '180'))

    $url = 'http://localhost:8080'
    $deadline = (Get-Date).AddSeconds(30)
    while ($true) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/health' -TimeoutSec 3
            if ($health.status -eq 'ok' -and $health.service -eq 'awanmarket') { break }
        }
        catch { }
        if ((Get-Date) -ge $deadline) {
            throw 'The site did not respond on port 8080. Check whether the port is occupied and run docker compose logs app.'
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "AwanMarket is ready: $url" -ForegroundColor Green
    Write-Host 'Use stop-site.bat to stop the site. Purchases and accounts remain in the database.'
    if (-not $NoBrowser) {
        try { Start-Process -FilePath $url }
        catch { Write-Host "Open $url in your browser." }
    }
    exit 0
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'If the build failed, check Docker Desktop, your connection and free disk space.'
    exit 1
}
