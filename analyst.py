import json
import os
import glob
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class IntelAnalyst:
    def __init__(self):
        print("[*] Loading Neural Network Models (spaCy & VADER)...")
        
        # Download spaCy model if not already installed (for Streamlit Cloud)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("[*] Downloading spaCy language model...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
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
        import re
        # Combine title and description for better context
        text = f"{article['title']}. {article['description']}"

        # 1. SENTIMENT ANALYSIS
        sentiment_score = self.sentiment_analyzer.polarity_scores(text)['compound']

        # 2. NAMED ENTITY RECOGNITION (NER)
        doc = self.nlp(text)
        entities = []

        # Normalization map for common country/entity variants
        normalization_map = {
            # US variants
            "us": "United States",
            "u.s.": "United States",
            "u.s": "United States",
            "u.s.a.": "United States",
            "u.s.a": "United States",
            "usa": "United States",
            "united states": "United States",
            "the united states": "United States",
            # UK variants
            "uk": "United Kingdom",
            "u.k.": "United Kingdom",
            "u.k": "United Kingdom",
            "united kingdom": "United Kingdom",
            "the united kingdom": "United Kingdom",
            # Add more as needed
        }

        def normalize_entity(text, label):
            # Remove leading 'the', punctuation, and lowercase
            norm = text.strip()
            norm = re.sub(r'^the\s+', '', norm, flags=re.IGNORECASE)
            norm = re.sub(r'[\.,;:!?"\'\(\)\[\]]', '', norm)
            norm = norm.strip().lower()
            # Singularize simple plurals for ORG/GPE (e.g., Oscars -> Oscar)
            if label in ("ORG", "GPE") and norm.endswith('s') and len(norm) > 3:
                norm = norm[:-1]
            # Map to canonical name if in normalization_map
            norm = normalization_map.get(norm, norm.title())
            return norm

        # We only care about specific types of entities for Intel
        target_labels = ["GPE", "ORG", "PERSON", "NORP"]

        # Collect all PERSON entities for last-name matching
        person_entities = []
        for ent in doc.ents:
            if ent.label_ in target_labels:
                norm_text = normalize_entity(ent.text, ent.label_)
                if ent.label_ == "PERSON":
                    person_entities.append(norm_text)
                entities.append((norm_text, ent.label_))

        # Improved PERSON merging: only merge single-token names to a full name if unambiguous
        if person_entities:
            # Build a map of last name -> list of full names
            last_name_map = {}
            for full in sorted(person_entities, key=len, reverse=True):
                tokens = full.split()
                if len(tokens) > 1:
                    last = tokens[-1]
                    last_name_map.setdefault(last, set()).add(full)
            def get_full_name(name):
                tokens = name.split()
                if len(tokens) == 1 and name in last_name_map:
                    full_names = last_name_map[name]
                    if len(full_names) == 1:
                        return list(full_names)[0]
                return name
            new_entities = []
            for ent_text, ent_label in entities:
                if ent_label == "PERSON":
                    ent_text = get_full_name(ent_text)
                new_entities.append((ent_text, ent_label))
            entities = new_entities

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
        structured_intel = analyst.process_batch(raw_data)
        
        # 4. Save Results
        analyst.save_processed_intel(structured_intel)
        
        # 5. Show a sample
        if structured_intel:
            print("\n--- ANALYST REPORT SAMPLE ---")
            sample = structured_intel[0]
            print(f"Headline: {sample['title']}")
            print(f"Sentiment Score: {sample['sentiment']} (Range: -1.0 to 1.0)")
            print(f"Detected Entities: {sample['entities']}")
    else:
        print("[!] No intelligence files found. Run collector.py first.")