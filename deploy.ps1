#!/usr/bin/env pwsh
# Deployment script for OSINT Conflict Monitor

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('local', 'docker', 'docker-compose')]
    [string]$Mode = 'local'
)

Write-Host "OSINT Conflict Monitor - Deployment" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Deployment Mode: $Mode" -ForegroundColor Yellow
Write-Host ""

# Check prerequisites
$allGood = $true

if ($Mode -eq 'local') {
    Write-Host "[Step 1/4] Checking prerequisites..." -ForegroundColor Yellow
    
    # Check Python
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.([0-9]+)") {
        Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Python 3.10+ not found" -ForegroundColor Red
        $allGood = $false
    }
    
    # Check virtual environment
    if (Test-Path ".venv") {
        Write-Host "  [OK] Virtual environment exists" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Virtual environment not found. Run setup.ps1" -ForegroundColor Red
        $allGood = $false
    }
    
    # Check .env
    if (Test-Path ".env") {
        $envContent = Get-Content .env -Raw
        if ($envContent -match "API_KEY=(.+)") {
            $apiKey = $matches[1].Trim()
            if ($apiKey -and $apiKey -ne "your_actual_newsapi_key_here") {
                Write-Host "  [OK] API key configured" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] API key not configured in .env" -ForegroundColor Red
                $allGood = $false
            }
        }
    } else {
        Write-Host "  [ERROR] .env file not found" -ForegroundColor Red
        $allGood = $false
    }
    
    if (-not $allGood) {
        Write-Host ""
        Write-Host "[FAILED] Prerequisites check failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "[Step 2/4] Activating environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
    Write-Host "  [OK] Environment activated" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "[Step 3/4] Initializing database..." -ForegroundColor Yellow
    
    $dbCode = @"
from archivist import IntelArchivist
archivist = IntelArchivist()
archivist.connect()
archivist.create_schema()
archivist.close()
print('  [OK] Database initialized')
"@
    $dbCode | python
    
    Write-Host ""
    Write-Host "[Step 4/4] Starting Streamlit dashboard..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Dashboard will open at: http://localhost:8501" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    
    streamlit run dashboard.py
}

elseif ($Mode -eq 'docker') {
    Write-Host "[Step 1/4] Checking Docker..." -ForegroundColor Yellow
    
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Docker: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Docker not found. Please install Docker Desktop" -ForegroundColor Red
        exit 1
    }
    
    # Check .env
    if (-not (Test-Path ".env")) {
        Write-Host "  [ERROR] .env file not found" -ForegroundColor Red
        Write-Host "     Create .env with: API_KEY=your_key" -ForegroundColor Yellow
        exit 1
    }
    
    $envContent = Get-Content .env -Raw
    if ($envContent -match "API_KEY=(.+)") {
        $apiKey = $matches[1].Trim()
        if ($apiKey -and $apiKey -ne "your_actual_newsapi_key_here") {
            Write-Host "  [OK] API key configured" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] API key not configured" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host ""
    Write-Host "[Step 2/4] Building Docker image..." -ForegroundColor Yellow
    docker build -t osint-conflict-monitor:latest .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Docker image built" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Docker build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "[Step 3/4] Stopping existing containers..." -ForegroundColor Yellow
    docker stop osint-conflict-monitor 2>&1 | Out-Null
    docker rm osint-conflict-monitor 2>&1 | Out-Null
    Write-Host "  [OK] Cleanup complete" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "[Step 4/4] Starting container..." -ForegroundColor Yellow
    
    # Read API key from .env
    $apiKeyValue = (Get-Content .env | Select-String "API_KEY=(.+)").Matches.Groups[1].Value
    
    docker run -d `
        --name osint-conflict-monitor `
        -p 8501:8501 `
        -e API_KEY=$apiKeyValue `
        -v "${PWD}/intel_data:/app/intel_data" `
        -v "${PWD}/intel_graph.db:/app/intel_graph.db" `
        osint-conflict-monitor:latest
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Container started" -ForegroundColor Green
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "[SUCCESS] Deployment Complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Dashboard URL: http://localhost:8501" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Useful commands:" -ForegroundColor Yellow
        Write-Host "  View logs:      docker logs osint-conflict-monitor -f" -ForegroundColor White
        Write-Host "  Stop container: docker stop osint-conflict-monitor" -ForegroundColor White
        Write-Host "  Start container: docker start osint-conflict-monitor" -ForegroundColor White
        Write-Host "  Remove container: docker rm osint-conflict-monitor" -ForegroundColor White
        Write-Host ""
        
        # Wait and check health
        Write-Host "Waiting for container to be healthy..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $status = docker inspect osint-conflict-monitor --format='{{.State.Health.Status}}' 2>&1
        if ($status -eq "healthy" -or $status -eq "starting") {
            Write-Host "  [OK] Container is healthy" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Container status: $status" -ForegroundColor Yellow
            Write-Host "     Check logs: docker logs osint-conflict-monitor" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [ERROR] Failed to start container" -ForegroundColor Red
        exit 1
    }
}

elseif ($Mode -eq 'docker-compose') {
    Write-Host "[Step 1/3] Checking Docker Compose..." -ForegroundColor Yellow
    
    $dockerComposeVersion = docker-compose --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Docker Compose: $dockerComposeVersion" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Docker Compose not found" -ForegroundColor Red
        exit 1
    }
    
    # Check files
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Host "  [ERROR] docker-compose.yml not found" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Test-Path ".env")) {
        Write-Host "  [ERROR] .env file not found" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "[Step 2/3] Building services..." -ForegroundColor Yellow
    docker-compose build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  [OK] Build complete" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "[Step 3/3] Starting services..." -ForegroundColor Yellow
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Services started" -ForegroundColor Green
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "[SUCCESS] Deployment Complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Dashboard URL: http://localhost:8501" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Useful commands:" -ForegroundColor Yellow
        Write-Host "  View logs:    docker-compose logs -f" -ForegroundColor White
        Write-Host "  Stop services: docker-compose down" -ForegroundColor White
        Write-Host "  Restart:      docker-compose restart" -ForegroundColor White
        Write-Host "  View status:  docker-compose ps" -ForegroundColor White
        Write-Host ""
        
        # Show status
        Write-Host "Service Status:" -ForegroundColor Cyan
        docker-compose ps
    } else {
        Write-Host "  [ERROR] Failed to start services" -ForegroundColor Red
        Write-Host "     Check logs: docker-compose logs" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
