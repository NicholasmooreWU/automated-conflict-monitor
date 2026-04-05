import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

class IntelCollector:
    def __init__(self, api_key):
        """Initialize collector with API key."""
        self.api_key = api_key 
        self.base_url = "https://newsapi.org/v2/everything"
    
    def fetch_intel(self, topic, from_date=None, to_date=None):
        """
        Queries the Intelligence Source (NewsAPI) for articles about the topic.
        Optionally filters by date range (YYYY-MM-DD).
        """
        print(f"[*] Initiating collection for topic: {topic}...")
        params = {
            'q': topic,
            'sortBy': 'relevancy',
            'language': 'en',
            'apiKey': self.api_key,
        }
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            total_results = data.get('totalResults', 0)
            print(f"[+] Collection successful. Found {total_results} intelligence items.")
            return data.get('articles', [])
        except (requests.exceptions.RequestException, Exception) as e:
            print(f"[!] Network Error: {e}")
            return []

    def _sanitize_filename(self, text):
        """
        Sanitizes text to prevent path traversal attacks.
        Removes special characters and path separators.
        """
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text)
        # Remove dangerous dot-dot sequences that could traverse directories
        sanitized = re.sub(r'\.\.\.+', '', sanitized)  # Remove 3+ consecutive dots
        sanitized = re.sub(r'\.\.', '', sanitized)  # Remove .. sequences
        # Remove dots at the start (prevents relative paths)
        sanitized = sanitized.lstrip('.')
        # Limit length to prevent filesystem issues
        sanitized = sanitized[:100]
        return sanitized if sanitized else "unknown"

    def save_raw_intel(self, data, topic):
        """
        Saves the raw gathered intelligence to a JSON file.
        """
        if not data:
            print("[!] No data to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = self._sanitize_filename(topic)
        filename = f"raw_intel_{safe_topic}_{timestamp}.json"
        
        os.makedirs("intel_data", exist_ok=True)
        filepath = os.path.join("intel_data", filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"[+] Raw intelligence archived to: {filepath}")

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    if not API_KEY or API_KEY == "your_real_api_key_here":
        raise ValueError("API_KEY not set. Please set it in a .env file.")

    # 2. TARGET
    TARGET_TOPIC = "Middle East"

    # 3. RUN
    bot = IntelCollector(API_KEY)
    articles = bot.fetch_intel(TARGET_TOPIC)
    bot.save_raw_intel(articles, TARGET_TOPIC)