# 🧪 Testing & Implementation Guide

## Table of Contents
1. [Local Testing](#local-testing)
2. [Docker Implementation](#docker-implementation)
3. [Production Deployment](#production-deployment)
4. [Troubleshooting](#troubleshooting)

---

## 🔧 Local Testing

### Prerequisites
- Python 3.10+
- NewsAPI Key (get free from https://newsapi.org/)
- Git (for cloning/version control)

### Step 1: Environment Setup

```powershell
# Navigate to project directory
cd "C:\Users\nomoo\OneDrive\Documents\OSINT"

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```powershell
# Create .env file
@"
API_KEY=your_actual_newsapi_key_here
"@ | Out-File -FilePath .env -Encoding utf8
```

**IMPORTANT**: Replace `your_actual_newsapi_key_here` with your real NewsAPI key.

### Step 3: Run Unit Tests

```powershell
# Run all tests with coverage
pytest tests/ -v --cov=. --cov-report=html

# View coverage report
start htmlcov/index.html

# Run specific test file
pytest tests/test_collector.py -v

# Run with output
pytest tests/ -v -s
```

**Expected Output:**
```
tests/test_collector.py::TestIntelCollector::test_initialization PASSED
tests/test_collector.py::TestIntelCollector::test_sanitize_filename PASSED
tests/test_archivist.py::TestIntelArchivist::test_database_creation PASSED
tests/test_analyst.py::TestIntelAnalyst::test_sentiment_analysis PASSED

===== X passed in Y.YYs =====
```

### Step 4: Manual Integration Testing

#### A. Test Data Collection
```powershell
# Test collector independently
python -c "
from collector import IntelCollector
from dotenv import load_dotenv
import os

load_dotenv()
collector = IntelCollector(os.getenv('API_KEY'))
articles = collector.fetch_intel('Middle East', days_back=3)
print(f'✓ Collected {len(articles)} articles')

# Save data
collector.save_raw_intel(articles, 'Middle East')
print('✓ Data saved to intel_data/')
"
```

**Expected Output:**
```
[*] Initiating collection for topic: Middle East...
[+] Collection successful. Found 100 intelligence items.
✓ Collected 100 articles
✓ Data saved to intel_data/
```

#### B. Test Analysis & Archiving
```powershell
# Test analyst processing
python -c "
from analyst import IntelAnalyst

analyst = IntelAnalyst()
intel_data = analyst.load_latest_intel()
print(f'✓ Loaded {len(intel_data)} articles')

results = analyst.process_batch(intel_data)
print(f'✓ Analyzed {len(results)} articles')
print(f'✓ Extracted {sum(len(r[\"entities\"]) for r in results)} entities')
"
```

#### C. Test Database Storage
```powershell
# Test archivist ingestion
python -c "
from archivist import IntelArchivist

archivist = IntelArchivist()
archivist.connect()
archivist.create_schema()

# Find latest JSON file
import glob, os
files = glob.glob('intel_data/*.json')
latest = max(files, key=os.path.getctime)

archivist.ingest_data(latest, region='Middle East')
print('✓ Data ingested into database')

archivist.close()
"
```

#### D. Test Full Pipeline
```powershell
# Run complete workflow
python -c "
from collector import IntelCollector
from analyst import IntelAnalyst
from archivist import IntelArchivist
from dotenv import load_dotenv
import os

load_dotenv()

# Step 1: Collect
print('== STEP 1: COLLECTION ==')
collector = IntelCollector(os.getenv('API_KEY'))
articles = collector.fetch_intel('Ukraine', days_back=3)
collector.save_raw_intel(articles, 'Ukraine')

# Step 2: Analyze
print('\n== STEP 2: ANALYSIS ==')
analyst = IntelAnalyst()
intel_data = analyst.load_latest_intel()
results = analyst.process_batch(intel_data)

# Step 3: Archive
print('\n== STEP 3: ARCHIVING ==')
archivist = IntelArchivist()
archivist.connect()
archivist.create_schema()
latest_file = max(__import__('glob').glob('intel_data/*.json'), key=os.path.getctime)
archivist.ingest_data(latest_file, region='Ukraine')
archivist.close()

print('\n✓ PIPELINE COMPLETE')
"
```

### Step 5: Test Dashboard Locally

```powershell
# Launch Streamlit dashboard
streamlit run dashboard.py

# Should open browser at http://localhost:8501
```

**Manual Testing Checklist:**
- [ ] Dashboard loads without errors
- [ ] Region selector shows all 10 regions
- [ ] "Collect Intelligence" button works
- [ ] Network graph displays entities
- [ ] Entity cards show names and types
- [ ] Sentiment analysis displays correctly
- [ ] Top entities list updates
- [ ] Date filters work
- [ ] Export CSV downloads successfully

---

## 🐳 Docker Implementation

### Step 1: Build Docker Image

```powershell
# Build the image
docker build -t osint-conflict-monitor:latest .

# Verify build
docker images | Select-String "osint-conflict-monitor"
```

### Step 2: Test Docker Container Locally

```powershell
# Run single container (no docker-compose)
docker run -d `
  --name osint-test `
  -p 8501:8501 `
  -e API_KEY=your_actual_api_key `
  -v ${PWD}/intel_data:/app/intel_data `
  -v ${PWD}/intel_graph.db:/app/intel_graph.db `
  osint-conflict-monitor:latest

# Check logs
docker logs osint-test -f

# Access dashboard at http://localhost:8501

# Stop and remove when done
docker stop osint-test
docker rm osint-test
```

### Step 3: Use Docker Compose

```powershell
# Create .env file for docker-compose
@"
API_KEY=your_actual_newsapi_key_here
"@ | Out-File -FilePath .env -Encoding utf8

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop services
docker-compose down
```

**Health Check:**
```powershell
# Check container health
docker inspect osint-conflict-monitor | Select-String "Health"

# Manual health check
curl http://localhost:8501/_stcore/health
```

### Step 4: Verify Docker Deployment

1. **Check Container Status**: `docker ps` - Should show "healthy" status
2. **Access Dashboard**: Navigate to http://localhost:8501
3. **Test Data Persistence**: Stop and restart container, data should persist in volumes
4. **Check Logs**: `docker-compose logs` - No errors should appear

---

## 🚀 Production Deployment

### Option 1: Cloud VM Deployment (AWS EC2, Azure VM, Google Compute)

#### AWS EC2 Setup
```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Clone repository
git clone https://github.com/yourusername/osint-monitor.git
cd osint-monitor

# Create .env file
echo "API_KEY=your_real_api_key" > .env

# Deploy with Docker Compose
sudo docker-compose up -d

# Configure firewall (Security Group)
# Allow inbound traffic on port 8501
```

#### Access Dashboard
- Public URL: `http://your-ec2-public-ip:8501`
- For HTTPS, add nginx reverse proxy with Let's Encrypt SSL

### Option 2: Streamlit Cloud (Fastest for Demo)

1. **Push to GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/osint-monitor.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Visit: https://streamlit.io/cloud
   - Connect GitHub repository
   - Set environment variable: `API_KEY=your_key`
   - Deploy (free tier available)

3. **Result**: Get public URL like `https://yourusername-osint-monitor.streamlit.app`

### Option 3: Heroku (PaaS)

```powershell
# Install Heroku CLI
# Then run:

heroku login
heroku create osint-conflict-monitor
heroku config:set API_KEY=your_actual_api_key
git push heroku main
heroku open
```

### Option 4: Kubernetes (Advanced)

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: osint-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: osint-monitor
  template:
    metadata:
      labels:
        app: osint-monitor
    spec:
      containers:
      - name: osint-monitor
        image: osint-conflict-monitor:latest
        ports:
        - containerPort: 8501
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: osint-secrets
              key: api-key
---
apiVersion: v1
kind: Service
metadata:
  name: osint-service
spec:
  selector:
    app: osint-monitor
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

Deploy:
```bash
kubectl create secret generic osint-secrets --from-literal=api-key=your_key
kubectl apply -f k8s-deployment.yaml
kubectl get services
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'spacy'"
**Solution:**
```powershell
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

#### 2. "API Key Missing or Invalid"
**Solution:**
- Verify `.env` file exists in project root
- Check `.env` content: `Get-Content .env`
- Ensure no extra spaces: `API_KEY=key` (not `API_KEY = key`)
- Get new key at: https://newsapi.org/register

#### 3. "Database is locked"
**Solution:**
```powershell
# Close all Python processes
Get-Process python | Stop-Process -Force

# Delete lock file if exists
Remove-Item intel_graph.db-journal -ErrorAction SilentlyContinue

# Restart application
```

#### 4. "Docker Container Unhealthy"
**Solution:**
```powershell
# Check logs
docker logs osint-conflict-monitor

# Common fixes:
# 1. Verify port not in use
netstat -ano | findstr :8501

# 2. Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 5. "No articles collected" or "totalResults: 0"
**Solution:**
- Verify API key is valid
- Check NewsAPI quota (free tier: 100 requests/day)
- Try different search terms
- Check internet connectivity

#### 6. Streamlit Error: "Address already in use"
**Solution:**
```powershell
# Find process on port 8501
netstat -ano | findstr :8501

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or run on different port
streamlit run dashboard.py --server.port=8502
```

### Validation Commands

```powershell
# Check all dependencies installed
pip list | Select-String "streamlit|spacy|pandas|plotly|pyvis"

# Verify database schema
python -c "
import sqlite3
conn = sqlite3.connect('intel_graph.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
print('Tables:', [row[0] for row in cursor.fetchall()])
conn.close()
"

# Test API connection
python -c "
import requests, os
from dotenv import load_dotenv
load_dotenv()
r = requests.get('https://newsapi.org/v2/everything', params={'q': 'test', 'apiKey': os.getenv('API_KEY')})
print('API Status:', r.status_code)
"
```

---

## 📊 Performance Testing

### Load Testing with Locust

Create `locustfile.py`:
```python
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def view_dashboard(self):
        self.client.get("/")
    
    @task
    def filter_region(self):
        self.client.get("/?region=Middle+East")
```

Run:
```powershell
pip install locust
locust -f locustfile.py --host=http://localhost:8501
```

### Database Performance Monitoring

```python
import sqlite3
import time

conn = sqlite3.connect('intel_graph.db')
cursor = conn.cursor()

# Test query performance
start = time.time()
cursor.execute("SELECT COUNT(*) FROM entities")
result = cursor.fetchone()[0]
duration = time.time() - start

print(f"Query returned {result} entities in {duration:.3f}s")

# Add index for performance
cursor.execute("CREATE INDEX IF NOT EXISTS idx_article_region ON articles(region)")
conn.commit()
conn.close()
```

---

## 🎓 Resume/Portfolio Tips

### What to Highlight

1. **Architecture Diagram**: Show the data pipeline flow
2. **Security Features**: Mention path traversal protection, env variables
3. **NLP/AI Skills**: spaCy NER, sentiment analysis, entity extraction
4. **Data Engineering**: JSON → SQLite pipeline, normalization
5. **Containerization**: Docker, docker-compose expertise
6. **Testing**: Unit tests, integration tests, coverage reports
7. **Visualization**: Interactive network graphs, real-time dashboards
8. **Real-World Application**: OSINT, conflict monitoring, geopolitical analysis

### Live Demo Preparation

```powershell
# Quick demo setup script
$script = @"
# Start fresh
Remove-Item intel_graph.db -ErrorAction SilentlyContinue
Remove-Item intel_data/*.json -ErrorAction SilentlyContinue

# Collect data for demo
python -c 'from collector import *; from dotenv import load_dotenv; import os; load_dotenv(); c = IntelCollector(os.getenv(\"API_KEY\")); a = c.fetch_intel(\"Ukraine conflict\"); c.save_raw_intel(a, \"Ukraine\")'

# Process data
python -c 'from analyst import *; from archivist import *; import glob, os; analyst = IntelAnalyst(); data = analyst.load_latest_intel(); results = analyst.process_batch(data); archivist = IntelArchivist(); archivist.connect(); archivist.create_schema(); latest = max(glob.glob(\"intel_data/*.json\"), key=os.path.getctime); archivist.ingest_data(latest, \"Ukraine\"); archivist.close()'

# Launch dashboard
streamlit run dashboard.py
"@

$script | Out-File -FilePath demo.ps1
```

---

## 📝 Success Criteria

- [ ] All unit tests pass (100% of test suite)
- [ ] Integration test completes without errors
- [ ] Docker container runs and passes health checks
- [ ] Dashboard loads in <5 seconds
- [ ] Data collection works for all 10 regions
- [ ] Network graph displays 50+ entities
- [ ] No security warnings in code
- [ ] Documentation is complete and accurate
- [ ] Can demo end-to-end workflow in <3 minutes

---

**Need Help?** Check project README or create an issue on GitHub.
