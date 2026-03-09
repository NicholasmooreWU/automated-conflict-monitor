# Streamlit Cloud Deployment Guide

## How Public Access Works

Your dashboard now operates in **two modes**:

### 1. **Viewing Mode** (Public - No API Key Required)
- ✅ Anyone can access the dashboard
- ✅ View all pre-collected intelligence data
- ✅ Explore network graphs and analytics
- ✅ Filter by region and entity types
- ✅ Export data to CSV
- ❌ Cannot collect new intelligence

### 2. **Collection Mode** (Admin - API Key Required)
- ✅ Dashboard owner with configured API key
- ✅ Can collect fresh intelligence from NewsAPI
- ✅ Updates the database for all users to view

---

## Streamlit Cloud Setup

### Step 1: Deploy Your App

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Add Streamlit Cloud configuration with secrets support"
   git push origin main
   ```

2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"**
4. Connect your GitHub repository
5. Select branch: `main`
6. Main file path: `dashboard.py`
7. Click **"Deploy"**

### Step 2: Configure API Key Secret

1. In your Streamlit Cloud app dashboard, click **⋮** menu
2. Select **"Settings"**
3. Go to **"Secrets"** tab
4. Add your secrets in TOML format:

```toml
# .streamlit/secrets.toml format
API_KEY = "your_newsapi_key_here"
```

5. Click **"Save"**
6. Your app will automatically restart

### Step 3: Verify Deployment

1. Wait for app to restart
2. Check that the warning "⚠️ API Key not configured" is gone
3. Click **"Collect Fresh Intelligence"** to test
4. Share your public URL with others!

---

## For Public Users

Your public dashboard URL will be:
```
https://[your-username]-[repo-name].streamlit.app
```

Users can:
- View all collected intelligence data
- Interact with network graphs
- Apply filters and export data
- **No login or API key needed**

---

## Data Collection Workflow

```
[You: Dashboard Admin]
    ↓
Configure API_KEY in Streamlit Secrets
    ↓
Click "Collect Fresh Intelligence"
    ↓
Data collected → Analyzed → Saved to database
    ↓
[Public Users]
    ↓
View updated intelligence data (read-only)
```

---

## Troubleshooting

### "API_KEY not found" Error
- **Solution**: Add API_KEY to Streamlit Cloud secrets (see Step 2)
- **Note**: Public users will see pre-collected data and won't see this error

### App Won't Start (Health Check Failed)
- ✅ **Fixed**: Removed port configuration from config.toml
- ✅ **Fixed**: Added spaCy model to requirements.txt

### Database Empty on First Deploy
- **Solution**: Collect fresh intelligence using the sidebar button
- The app creates an empty database on first start
- You need to populate it with data collection

---

## Security Best Practices

✅ **API key stored securely** in Streamlit Cloud secrets  
✅ **Never commit** `.env` files or API keys to GitHub  
✅ **Public users** cannot access or see your API key  
✅ **Database** is read-only for public users (no collection button)

---

## Local Development

For local testing with API key:

1. Create `.env` file:
   ```
   API_KEY=your_newsapi_key_here
   ```

2. Run locally:
   ```bash
   streamlit run dashboard.py
   ```

3. The app will read from `.env` locally and from secrets in cloud

---

## Cost Considerations

- **Streamlit Cloud**: Free tier available (limited resources)
- **NewsAPI**: Free tier = 100 requests/day
- **Database**: SQLite stored in app's file system (reset on redeploy)
- **Tip**: Collect data periodically on local machine, commit the database file to keep historical data

---

## Need Help?

- Streamlit Docs: https://docs.streamlit.io
- Streamlit Cloud Secrets: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management
- NewsAPI Docs: https://newsapi.org/docs
