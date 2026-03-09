#!/usr/bin/env pwsh
# Setup script for OSINT Conflict Monitor
# Run this script to set up the project for the first time

Write-Host "OSINT Conflict Monitor - Setup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "[1/7] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.([0-9]+)") {
    $minorVersion = [int]$matches[1]
    if ($minorVersion -ge 10) {
        Write-Host "  [OK] Python version OK: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Python 3.10+ required. Current: $pythonVersion" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Step 2: Create virtual environment
Write-Host "[2/7] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "  [OK] Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv .venv
    Write-Host "  [OK] Virtual environment created" -ForegroundColor Green
}

# Step 3: Activate virtual environment
Write-Host "[3/7] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "  [OK] Virtual environment activated" -ForegroundColor Green

# Step 4: Install dependencies
Write-Host "[4/7] Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "  [OK] Dependencies installed" -ForegroundColor Green

# Step 5: Download spaCy model
Write-Host "[5/7] Downloading spaCy language model..." -ForegroundColor Yellow
python -m spacy download en_core_web_sm --quiet
Write-Host "  [OK] spaCy model downloaded" -ForegroundColor Green

# Step 6: Create necessary directories
Write-Host "[6/7] Creating project directories..." -ForegroundColor Yellow
if (-not (Test-Path "intel_data")) {
    New-Item -ItemType Directory -Path "intel_data" | Out-Null
}
Write-Host "  [OK] Directories created" -ForegroundColor Green

# Step 7: Check for .env file
Write-Host "[7/7] Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  [WARN] .env file not found. Creating template..." -ForegroundColor Yellow
    @"
# NewsAPI Configuration
API_KEY=your_actual_newsapi_key_here

# Get your free API key from: https://newsapi.org/register
"@ | Out-File -FilePath .env -Encoding utf8
    Write-Host "  [OK] .env template created" -ForegroundColor Green
    Write-Host ""
    Write-Host "  [WARN] IMPORTANT: Edit .env file and add your NewsAPI key!" -ForegroundColor Red
    Write-Host "     Get a free key at: https://newsapi.org/register" -ForegroundColor Cyan
} else {
    Write-Host "  [OK] .env file exists" -ForegroundColor Green
    
    # Check if API key is configured
    $envContent = Get-Content .env -Raw
    if ($envContent -match "your_actual_newsapi_key_here") {
        Write-Host "  [WARN] Default API key detected in .env" -ForegroundColor Red
        Write-Host "     Please update with your real NewsAPI key!" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Update .env with your NewsAPI key (if not done)" -ForegroundColor White
Write-Host "  2. Run tests: pytest tests/ -v" -ForegroundColor White
Write-Host "  3. Start dashboard: streamlit run dashboard.py" -ForegroundColor White
Write-Host ""
Write-Host "Quick Test:" -ForegroundColor Cyan
Write-Host '  python -c "from collector import IntelCollector; print(''Import successful!'')"' -ForegroundColor White
Write-Host ""
