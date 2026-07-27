# --- ENTITY EXTRACTION FILTERS ---
NOISE_ENTITIES = {"the", "a", "an", "this", "that", "us", "it", "he", "she", "they"}
MIN_ENTITY_LENGTH = 3

import json
import os
import glob
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import relevance

# Only keep analytically relevant entity types
RELEVANT_ENTITY_TYPES = {
    "GPE",    # Countries, cities, regions
    "ORG",    # Organizations, agencies, companies
    "PERSON", # Named individuals
    "NORP",   # Nationalities, political groups
    "FAC",    # Facilities - military bases, infrastructure
    "EVENT"   # Named events
}

class IntelAnalyst:
    # Preferred spaCy model, in order. en_core_web_lg gives noticeably
    # better NER than en_core_web_sm on multi-word entities (GPE/ORG
    # especially), which matters here since the network graph is built
    # entirely from extracted entities. Falls back to en_core_web_sm if
    # _lg can't be loaded/downloaded (e.g. a memory-constrained deployment
    # such as Streamlit Community Cloud's free tier), so the app still
    # runs -- just with weaker entity extraction.
    SPACY_MODEL_PREFERENCE = ("en_core_web_lg", "en_core_web_sm")

    def __init__(self):
        print("[*] Loading Neural Network Models (spaCy & VADER)...")
        self.nlp = self._load_spacy_model()

        # Load the sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def _load_spacy_model(self):
        """
        Try each model in SPACY_MODEL_PREFERENCE in order, downloading it
        if not already installed. Falls back to the next model in the list
        if one fails to load or download.
        """
        import subprocess
        last_error = None
        for model_name in self.SPACY_MODEL_PREFERENCE:
            try:
                return spacy.load(model_name)
            except OSError:
                print(f"[*] Downloading spaCy language model: {model_name}...")
                try:
                    subprocess.run(
                        ["python", "-m", "spacy", "download", model_name], check=True
                    )
                    return spacy.load(model_name)
                except Exception as e:
                    last_error = e
                    print(f"[!] Could not load {model_name}: {e}")
        raise RuntimeError(
            f"Failed to load any spaCy model from {self.SPACY_MODEL_PREFERENCE}: {last_error}"
        )

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
            # Smarter plural-stripping: only singularize single-word entities not in exceptions
            plural_exceptions = {"United Nations", "Los Angeles", "United States", "Armed Forces"}
            if (
                label in ("ORG", "GPE")
                and norm.endswith('s')
                and len(norm) > 3
                and ' ' not in norm
                and norm not in plural_exceptions
            ):
                norm = norm[:-1]
            # Map to canonical name if in normalization_map
            norm = normalization_map.get(norm, norm.title())
            return norm


        # Only keep analytically relevant entity types
        target_labels = RELEVANT_ENTITY_TYPES

        # Collect all PERSON entities for last-name matching
        person_entities = []
        filtered_entities = []
        for ent in doc.ents:
            # Only keep relevant types
            if ent.label_ not in target_labels:
                continue
            # Minimum character length
            if len(ent.text.strip()) < MIN_ENTITY_LENGTH:
                continue
            # Stopword/noise filter (case-insensitive)
            if ent.text.strip().lower() in NOISE_ENTITIES:
                continue
            norm_text = normalize_entity(ent.text, ent.label_)
            if ent.label_ == "PERSON":
                person_entities.append(norm_text)
            filtered_entities.append((norm_text, ent.label_))

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
            for ent_text, ent_label in filtered_entities:
                if ent_label == "PERSON":
                    ent_text = get_full_name(ent_text)
                new_entities.append((ent_text, ent_label))
            filtered_entities = new_entities

        # Return the structured data
        return {
            "title": article['title'],
            "source": article['source']['name'],
            "published_at": article['publishedAt'],
            "sentiment": sentiment_score,
            "entities": list(set(filtered_entities)) # Remove duplicates
        }

    def process_batch(self, articles, main_keyword=None, priority_keywords=None):
        """
        priority_keywords: optional list of topic-specific auto-pass terms
        for the active region/query (see relevance.score_article and
        dashboard.REGION_PRIORITY_KEYWORDS). Passing None falls back to
        scoring on main_keyword + the general keyword categories only.
        """
        processed_data = []
        print(f"[*] Analyzing {len(articles)} articles. This may take a moment...")
        for idx, article in enumerate(articles):
            # Skip articles specifically removed by the source
            if article.get('title') == "[Removed]":
                print(f"[SKIP] Article {idx}: Title is '[Removed]'.")
                continue

            source = article.get('source', '')
            if isinstance(source, dict):
                source = source.get('name', '')

            score, reason = relevance.score_article(
                article.get('title', ''),
                article.get('description', ''),
                source=source,
                priority_keywords=priority_keywords,
                main_keyword=main_keyword,
            )
            if not relevance.is_relevant(reason):
                print(f"[SKIP] Article {idx}: {reason}. Title: {article.get('title', '')}")
                article['irrelevant'] = True
                continue

            analysis = self.analyze_article(article)
            analysis['relevance_score'] = score
            analysis['filter_reason'] = reason
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