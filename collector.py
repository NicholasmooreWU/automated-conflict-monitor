import requests
import json
import os
from datetime import datetime

class IntelCollector:
    def __init__(self, api_key):
        self.api_key = "7300ab8185364e989089f03981f2db1f"
        self.base_url = "https://newsapi.org/v2/everything"
    
    def fetch_intel(self, topic, days_back=3):
        """
        Queries the Intelligence Source (NewsAPI) for articles about the topic.
        """
        print(f"[*] Initiating collection for topic: {topic}...")
        
        # Calculate date range (collect intel from the last N days)
        # Note: Free tier allows up to 1 month back.
        params = {
            'q': topic,
            'sortBy': 'relevancy',
            'language': 'en',
            'apiKey': self.api_key,
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status() # Check for HTTP errors
            data = response.json()
            
            total_results = data.get('totalResults', 0)
            print(f"[+] Collection successful. Found {total_results} intelligence items.")
            return data.get('articles', [])
            
        except requests.exceptions.RequestException as e:
            print(f"[!] Network Error: {e}")
            return []

    def save_raw_intel(self, data, topic):
        """
        Saves the raw gathered intelligence to a JSON file (Data Lake concept).
        """
        if not data:
            print("[!] No data to save.")
            return

        # Create a timestamped filename so we don't overwrite history
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_intel_{topic}_{timestamp}.json"
        
        # Ensure a directory exists
        os.makedirs("intel_data", exist_ok=True)
        filepath = os.path.join("intel_data", filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"[+] Raw intelligence archived to: {filepath}")

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # 1. SETUP: Paste your API key here
    # (In a real gov env, we would use environment variables for security)
    API_KEY = "YOUR_API_KEY_HERE"  
    
    # 2. TARGET: What are we monitoring?
    TARGET_TOPIC = "South China Sea" # Try: "Cyber Warfare", "Ukraine", "Semiconductors"

    # 3. RUN: Initialize the Collector
    bot = IntelCollector(API_KEY)
    
    # 4. COLLECT: Fetch data
    articles = bot.fetch_intel(TARGET_TOPIC)
    
    # 5. STORE: Save to disk
    bot.save_raw_intel(articles, TARGET_TOPIC)
    
    # 6. VERIFY: Print the first 3 headlines to prove it works
    print("\n--- LATEST INTELLIGENCE HEADLINES ---")
    for i, article in enumerate(articles[:3]):
        print(f"{i+1}. {article['title']} ({article['source']['name']})")