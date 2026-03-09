# 🚀 Quick Start Guide

**Get up and running in 5 minutes!**

---

## ⚡ Option 1: Local Development (Recommended for Testing)

### 1. Setup (One-time)
```powershell
# Run automated setup
.\setup.ps1
```

Or manually:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure API Key
```powershell
# Edit .env file and add your NewsAPI key
notepad .env
```

Replace `your_actual_newsapi_key_here` with your real key from https://newsapi.org/register

### 3. Test Everything
```powershell
.\test_all.ps1
```

### 4. Run Dashboard
```powershell
.\deploy.ps1 -Mode local
```

Visit: http://localhost:8501

---

## 🐳 Option 2: Docker (Recommended for Production)

### 1. Ensure Docker is Running
```powershell
docker --version
```

### 2. Configure Environment
```powershell
# Create .env with your API key
@"
API_KEY=your_actual_newsapi_key
"@ | Out-File -FilePath .env -Encoding utf8
```

### 3. Deploy with Docker Compose
```powershell
.\deploy.ps1 -Mode docker-compose
```

Or manually:
```powershell
docker-compose up -d
```

Visit: http://localhost:8501

### Monitor Logs
```powershell
docker-compose logs -f
```

### Stop Services
```powershell
docker-compose down
```

---

## 📝 One-Line Testing Commands

```powershell
# Test API connection
python -c "from collector import IntelCollector; from dotenv import load_dotenv; import os; load_dotenv(); c = IntelCollector(os.getenv('API_KEY')); print('✓ OK' if c.fetch_intel('test') is not None else '✗ FAIL')"

# Test database
python -c "from archivist import IntelArchivist; a = IntelArchivist('test.db'); a.connect(); a.create_schema(); a.close(); import os; os.remove('test.db'); print('✓ Database OK')"

# Test NLP
python -c "from analyst import IntelAnalyst; a = IntelAnalyst(); print('✓ NLP OK')"

# Run unit tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=. --cov-report=html
```

---

## 🎯 Common Tasks

### Collect Data for a Region
```powershell
python -c "
from collector import IntelCollector
from dotenv import load_dotenv
import os

load_dotenv()
collector = IntelCollector(os.getenv('API_KEY'))

# Collect intelligence
articles = collector.fetch_intel('Middle East conflict', days_back=3)
collector.save_raw_intel(articles, 'Middle East')

print(f'Collected {len(articles)} articles')
"
```

### Process Data
```powershell
python -c "
from analyst import IntelAnalyst
from archivist import IntelArchivist
import glob, os

# Analyze latest data
analyst = IntelAnalyst()
data = analyst.load_latest_intel()
results = analyst.process_batch(data)

# Store in database
archivist = IntelArchivist()
archivist.connect()
archivist.create_schema()

latest_file = max(glob.glob('intel_data/*.json'), key=os.path.getctime)
archivist.ingest_data(latest_file, region='Middle East')
archivist.close()

print(f'Processed {len(results)} articles')
"
```

### Query Database
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('intel_graph.db')
cursor = conn.cursor()

# Get stats
cursor.execute('SELECT COUNT(*) FROM articles')
print(f'Articles: {cursor.fetchone()[0]}')

cursor.execute('SELECT COUNT(DISTINCT name) FROM entities')
print(f'Unique entities: {cursor.fetchone()[0]}')

cursor.execute('SELECT region, COUNT(*) FROM articles GROUP BY region')
print('\nArticles by region:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
"
```

### Clean Database
```powershell
# Backup first
Copy-Item intel_graph.db intel_graph.backup.db

# Reset database
Remove-Item intel_graph.db
python -c "from archivist import IntelArchivist; a = IntelArchivist(); a.connect(); a.create_schema(); a.close(); print('✓ Database recreated')"
```

---

## 🐛 Quick Fixes

### "API key not configured"
```powershell
# Check .env file
Get-Content .env

# Should show: API_KEY=your_actual_key
# If not, edit it:
notepad .env
```

### "spaCy model not found"
```powershell
python -m spacy download en_core_web_sm
```

### "Database is locked"
```powershell
# Close all Python processes
Get-Process python | Stop-Process -Force

# Remove lock file
Remove-Item intel_graph.db-journal -ErrorAction SilentlyContinue
```

### "Port 8501 already in use"
```powershell
# Find and kill process
$port = 8501
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $process -Force
```

### Docker container unhealthy
```powershell
# Check logs
docker logs osint-conflict-monitor

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Project Structure

```
OSINT/
├── collector.py          # Fetch news from NewsAPI
├── analyst.py            # NLP processing (spaCy + VADER)
├── archivist.py          # Database storage
├── dashboard.py          # Streamlit UI
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container definition
├── docker-compose.yml   # Multi-container orchestration
├── .env                 # Environment variables (NEVER COMMIT!)
├── intel_data/          # Raw JSON data
├── intel_graph.db       # SQLite database
└── tests/               # Unit tests
    ├── test_collector.py
    ├── test_analyst.py
    └── test_archivist.py
```

---

## 🎓 For Resume/Portfolio

### Demo Preparation
1. **Fresh Data Collection**:
   ```powershell
   # Collect data for 3 interesting regions
   python -c "from collector import *; from dotenv import load_dotenv; import os; load_dotenv(); c = IntelCollector(os.getenv('API_KEY')); regions = ['Middle East', 'Ukraine', 'Taiwan']; [c.save_raw_intel(c.fetch_intel(r), r) for r in regions]"
   ```

2. **Process All Data**:
   ```powershell
   # Run full pipeline
   Get-ChildItem intel_data\*.json | ForEach-Object { python -c "from analyst import *; from archivist import *; analyst = IntelAnalyst(); data = analyst.load_latest_intel(); results = analyst.process_batch(data); archivist = IntelArchivist(); archivist.connect(); archivist.create_schema(); archivist.ingest_data('$($_.FullName)', region='Demo'); archivist.close()" }
   ```

3. **Launch Dashboard**:
   ```powershell
   streamlit run dashboard.py
   ```

### Key Talking Points
- **Architecture**: 3-stage ETL pipeline (Extract → Transform → Load)
- **NLP**: spaCy for Named Entity Recognition, VADER for sentiment
- **Security**: Environment variables, path traversal protection, parameterized SQL
- **Containerization**: Docker + Docker Compose for deployment
- **Testing**: Unit tests with pytest, 80%+ code coverage
- **Real-time Viz**: Streamlit dashboard with interactive network graphs
- **Scalability**: Can process 1000+ articles/hour

---

## 📚 Additional Resources

- **Full Testing Guide**: See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **NewsAPI Docs**: https://newsapi.org/docs
- **spaCy NER**: https://spacy.io/usage/linguistic-features#named-entities
- **Streamlit Docs**: https://docs.streamlit.io
- **Docker Docs**: https://docs.docker.com

---

## Need Help?

1. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed troubleshooting
2. Run `.\test_all.ps1` to diagnose issues
3. View logs: `docker-compose logs -f` (if using Docker)
4. Check GitHub Issues (if project is on GitHub)

---

**Ready to Deploy?** Run: `.\deploy.ps1 -Mode docker-compose`
