#!/usr/bin/env pwsh
# Comprehensive testing script for OSINT Conflict Monitor

Write-Host "Running OSINT Conflict Monitor Test Suite" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Virtual environment not found. Run setup.ps1 first" -ForegroundColor Red
    exit 1
}

# Check .env file
$apiKeyConfigured = $false
if (Test-Path ".env") {
    $envContent = Get-Content .env -Raw
    if ($envContent -match "API_KEY=(.+)") {
        $apiKey = $matches[1].Trim()
        if ($apiKey -and $apiKey -ne "your_actual_newsapi_key_here") {
            $apiKeyConfigured = $true
            Write-Host "[OK] API key configured" -ForegroundColor Green
        }
    }
}

if (-not $apiKeyConfigured) {
    Write-Host "[WARN] API key not configured in .env file" -ForegroundColor Yellow
    Write-Host "   Integration tests will be skipped" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST 1: Unit Tests" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (Test-Path "tests") {
    pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
    $unitTestResult = $LASTEXITCODE
    
    if ($unitTestResult -eq 0) {
        Write-Host "[OK] Unit tests passed" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Unit tests failed" -ForegroundColor Red
    }
} else {
    Write-Host "[WARN] No test directory found" -ForegroundColor Yellow
    $unitTestResult = 0
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST 2: Code Quality Checks" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check imports
Write-Host "Checking core imports..." -ForegroundColor Yellow
$checkCode = @"
try:
    import streamlit
    import spacy
    import pandas
    import plotly
    import networkx
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    print('[OK] All core dependencies importable')
except ImportError as e:
    print(f'[ERROR] Import error: {e}')
    exit(1)
"@
$checkCode | python
$importResult = $LASTEXITCODE

# Check spaCy model
Write-Host "Checking spaCy model..." -ForegroundColor Yellow
$spacyCode = @"
import spacy
try:
    nlp = spacy.load('en_core_web_sm')
    print('[OK] spaCy model loaded successfully')
except Exception as e:
    print(f'[ERROR] spaCy model error: {e}')
    exit(1)
"@
$spacyCode | python
$spacyResult = $LASTEXITCODE

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST 3: Module Functionality" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

Write-Host "Testing collector module..." -ForegroundColor Yellow
$collectorCode = @"
from collector import IntelCollector
collector = IntelCollector('test_key')
sanitized = collector._sanitize_filename('../../../test')
assert '..' not in sanitized, 'Sanitization failed'
print('[OK] Collector module working')
"@
$collectorCode | python
$collectorResult = $LASTEXITCODE

Write-Host "Testing analyst module..." -ForegroundColor Yellow
$analystCode = @"
from analyst import IntelAnalyst
analyst = IntelAnalyst()
print('[OK] Analyst module working')
"@
$analystCode | python
$analystResult = $LASTEXITCODE

Write-Host "Testing archivist module..." -ForegroundColor Yellow
$archivistCode = @"
from archivist import IntelArchivist
import os
# Use test database
archivist = IntelArchivist('test_db.db')
archivist.connect()
archivist.create_schema()
archivist.close()
os.remove('test_db.db')
print('[OK] Archivist module working')
"@
$archivistCode | python
$archivistResult = $LASTEXITCODE

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST 4: Integration Test (Optional)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$integrationResult = 0
if ($apiKeyConfigured) {
    Write-Host "Testing full pipeline..." -ForegroundColor Yellow
    
    $integrationCode = @"
from collector import IntelCollector
from dotenv import load_dotenv
import os

load_dotenv()
collector = IntelCollector(os.getenv('API_KEY'))

# Test API connection
try:
    articles = collector.fetch_intel('test', days_back=1)
    if articles:
        print(f'[OK] API connection successful ({len(articles)} articles)')
    else:
        print('[OK] API connection successful (0 articles returned)')
except Exception as e:
    print(f'[ERROR] API test failed: {e}')
    exit(1)
"@
    $integrationCode | python
    $integrationResult = $LASTEXITCODE
} else {
    Write-Host "[WARN] Skipped (API key not configured)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST 5: Docker Configuration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

if (Test-Path "Dockerfile") {
    Write-Host "[OK] Dockerfile exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Dockerfile not found" -ForegroundColor Red
}

if (Test-Path "docker-compose.yml") {
    Write-Host "[OK] docker-compose.yml exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] docker-compose.yml not found" -ForegroundColor Red
}

if (Test-Path ".dockerignore") {
    Write-Host "[OK] .dockerignore exists" -ForegroundColor Green
} else {
    Write-Host "[WARN] .dockerignore not found (recommended)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = ($unitTestResult -eq 0) -and 
             ($importResult -eq 0) -and 
             ($spacyResult -eq 0) -and
             ($collectorResult -eq 0) -and 
             ($analystResult -eq 0) -and 
             ($archivistResult -eq 0) -and
             ($integrationResult -eq 0)

if ($allPassed) {
    Write-Host "[SUCCESS] ALL TESTS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your project is ready for deployment!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  - Run dashboard: streamlit run dashboard.py" -ForegroundColor White
    Write-Host "  - Build Docker: docker build -t osint-monitor ." -ForegroundColor White
    Write-Host "  - View coverage: start htmlcov/index.html" -ForegroundColor White
} else {
    Write-Host "[WARN] SOME TESTS FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Review the output above for details" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Test artifacts:" -ForegroundColor Cyan
Write-Host "  - Coverage report: htmlcov/index.html" -ForegroundColor White
Write-Host "  - Test database: (cleaned up)" -ForegroundColor White
Write-Host ""
