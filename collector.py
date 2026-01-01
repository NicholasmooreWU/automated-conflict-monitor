import requests
import json
import os
from datetime import datetime

class IntelCollector:
    def __init__(self, api_key):
        # SECURITY FIX: Do not hardcode the key here. 
        # Use the variable passed in from the outside.
        self.api_key = api_key 
        self.base_url = "https://newsapi.org/v2/everything"
    
    def fetch_intel(self, topic, days_back=3):
        """
        Queries the Intelligence Source (NewsAPI) for articles about the topic.
        """
        print(f"[*] Initiating collection for topic: {topic}...")
        
        params = {
            'q': topic,
            'sortBy': 'relevancy',
            'language': 'en',
            'apiKey': self.api_key,
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            total_results = data.get('totalResults', 0)
            print(f"[+] Collection successful. Found {total_results} intelligence items.")
            return data.get('articles', [])
            
        except requests.exceptions.RequestException as e:
            print(f"[!] Network Error: {e}")
            return []

    def save_raw_intel(self, data, topic):
        """
        Saves the raw gathered intelligence to a JSON file.
        """
        if not data:
            print("[!] No data to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_intel_{topic}_{timestamp}.json"
        
        os.makedirs("intel_data", exist_ok=True)
        filepath = os.path.join("intel_data", filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"[+] Raw intelligence archived to: {filepath}")

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # 1. SETUP: Put the key here for local testing, 
    # BUT change it to "YOUR_API_KEY" before committing to GitHub!
    API_KEY = "7300ab8185364e989089f03981f2db1f"  
    
    # 2. TARGET
    TARGET_TOPIC = "South China Sea" 

    # 3. RUN
    bot = IntelCollector(API_KEY)
    articles = bot.fetch_intel(TARGET_TOPIC)
    bot.save_raw_intel(articles, TARGET_TOPIC)