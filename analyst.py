import json
import os
import glob
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class IntelAnalyst:
    def __init__(self):
        print("[*] Loading Neural Network Models (spaCy & VADER)...")
        # Load the English language model
        self.nlp = spacy.load("en_core_web_sm")
        # Load the sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def load_latest_intel(self):
        """
        Finds the most recent raw intelligence file in the intel_data folder.
        """
        # Look for all json files in the folder
        list_of_files = glob.glob('intel_data/*.json') 
        if not list_of_files:
            return None
        
        # Get the one with the most recent creation time
        latest_file = max(list_of_files, key=os.path.getctime)
        print(f"[+] Loaded latest intelligence batch: {latest_file}")
        
        with open(latest_file, 'r') as f:
            return json.load(f)

    def analyze_article(self, article):
        """
        Extracts Entities and Sentiment from a single article.
        """
        # Combine title and description for better context
        text = f"{article['title']}. {article['description']}"
        
        # 1. SENTIMENT ANALYSIS
        # Returns a score: -1 (Negative) to +1 (Positive)
        sentiment_score = self.sentiment_analyzer.polarity_scores(text)['compound']

        # 2. NAMED ENTITY RECOGNITION (NER)
        doc = self.nlp(text)
        entities = []
        
        # We only care about specific types of entities for Intel
        target_labels = ["GPE", "ORG", "PERSON", "NORP"] 
        # GPE: Countries/Cities, ORG: Organizations, NORP: Nationalities
        
        for ent in doc.ents:
            if ent.label_ in target_labels:
                entities.append((ent.text, ent.label_))
        
        # Return the structured data
        return {
            "title": article['title'],
            "source": article['source']['name'],
            "published_at": article['publishedAt'],
            "sentiment": sentiment_score,
            "entities": list(set(entities)) # Remove duplicates
        }

    def process_batch(self, articles):
        processed_data = []
        print(f"[*] Analyzing {len(articles)} articles. This may take a moment...")
        
        for article in articles:
            # Skip articles specifically removed by the source
            if article['title'] == "[Removed]":
                continue
                
            analysis = self.analyze_article(article)
            processed_data.append(analysis)
            
        return processed_data

    def save_processed_intel(self, data):
        filename = "processed_intel.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[+] Analysis complete. Processed intelligence saved to {filename}")

if __name__ == "__main__":
    # 1. Initialize Analyst
    analyst = IntelAnalyst()
    
    # 2. Load Raw Data
    raw_data = analyst.load_latest_intel()
    
    if raw_data:
        # 3. Process the Data
        # We limit to first 20 articles for speed during testing
        structured_intel = analyst.process_batch(raw_data[:20])
        
        # 4. Save Results
        analyst.save_processed_intel(structured_intel)
        
        # 5. Show a sample
        print("\n--- ANALYST REPORT SAMPLE ---")
        sample = structured_intel[0]
        print(f"Headline: {sample['title']}")
        print(f"Sentiment Score: {sample['sentiment']} (Range: -1.0 to 1.0)")
        print(f"Detected Entities: {sample['entities']}")
    else:
        print("[!] No intelligence files found. Run collector.py first.")