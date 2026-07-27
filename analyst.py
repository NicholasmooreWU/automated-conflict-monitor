# --- ENTITY EXTRACTION FILTERS ---
NOISE_ENTITIES = {"the", "a", "an", "this", "that", "us", "it", "he", "she", "they"}
MIN_ENTITY_LENGTH = 3

import json
import os
import glob
import re
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

# Normalization map for common country/entity variants
NORMALIZATION_MAP = {
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

PLURAL_EXCEPTIONS = {"united nations", "los angeles", "united states", "armed forces"}

# Known cases where spaCy's models (especially en_core_web_lg) misclassify
# a proper noun's entity TYPE, not just its text. Keyed by lowercased,
# stripped entity text -> the label it should actually be treated as.
# Add to this as you spot more mislabeled terms in real data.
LABEL_CORRECTIONS = {
    "oscars": "ORG",
    "grammys": "ORG",
    "emmys": "ORG",
}


def normalize_entity(text, label):
    """
    Normalize an extracted entity's surface text to a canonical form.
    Pulled out to module level (rather than a closure inside
    analyze_article) so it can be unit-tested directly without going
    through live spaCy inference -- which is what let the "Oscars"
    mislabeling bug hide inside an NER-dependent test in the first place.
    """
    norm = text.strip()
    norm = re.sub(r'^the\s+', '', norm, flags=re.IGNORECASE)
    norm = re.sub(r'[\.,;:!?"\'\(\)\[\]]', '', norm)
    norm = norm.strip().lower()
    # Singularize simple plurals for ORG/GPE (e.g., Oscars -> Oscar)
    if (
        label in ("ORG", "GPE")
        and norm.endswith('s')
        and len(norm) > 3
        and ' ' not in norm
        and norm not in PLURAL_EXCEPTIONS
    ):
        norm = norm[:-1]
    # Map to canonical name if in normalization_map
    norm = NORMALIZATION_MAP.get(norm, norm.title())
    return norm


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
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def _load_spacy_model(self):
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
        list_of_files = glob.glob('intel_data/*.json')
        if not list_of_files:
            return None
        latest_file = max(list_of_files, key=os.path.getctime)
        print(f"[+] Loaded latest intelligence batch: {latest_file}")
        with open(latest_file, 'r') as f:
            return json.load(f)

    def analyze_article(self, article):
        """
        Extracts Entities and Sentiment from a single article.
        """
        title = article.get('title') or ''
        description = article.get('description') or ''
        text = f"{title}. {description}".strip()

        # 1. SENTIMENT ANALYSIS
        sentiment_score = self.sentiment_analyzer.polarity_scores(text)['compound']

        # 2. NAMED ENTITY RECOGNITION (NER)
        doc = self.nlp(text)

        person_entities = []
        filtered_entities = []
        for ent in doc.ents:
            ent_text = ent.text.strip()
            # Apply known label corrections BEFORE the type filter, so a
            # term like "Oscars" is treated as ORG even if this particular
            # model guessed PERSON.
            label = LABEL_CORRECTIONS.get(ent_text.lower(), ent.label_)

            if label not in RELEVANT_ENTITY_TYPES:
                continue
            if len(ent_text) < MIN_ENTITY_LENGTH:
                continue
            if ent_text.lower() in NOISE_ENTITIES:
                continue

            norm_text = normalize_entity(ent_text, label)
            if label == "PERSON":
                person_entities.append(norm_text)
            filtered_entities.append((norm_text, label))

        # Improved PERSON merging: only merge single-token names to a full name if unambiguous
        if person_entities:
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

        return {
            "title": article['title'],
            "source": article['source']['name'],
            "published_at": article['publishedAt'],
            "sentiment": sentiment_score,
            "entities": list(set(filtered_entities))
        }

    def process_batch(self, articles, main_keyword=None, priority_keywords=None):
        processed_data = []
        print(f"[*] Analyzing {len(articles)} articles. This may take a moment...")
        for idx, article in enumerate(articles):
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
    analyst = IntelAnalyst()
    raw_data = analyst.load_latest_intel()
    if raw_data:
        structured_intel = analyst.process_batch(raw_data)
        analyst.save_processed_intel(structured_intel)
        if structured_intel:
            print("\n--- ANALYST REPORT SAMPLE ---")
            sample = structured_intel[0]
            print(f"Headline: {sample['title']}")
            print(f"Sentiment Score: {sample['sentiment']} (Range: -1.0 to 1.0)")
            print(f"Detected Entities: {sample['entities']}")
    else:
        print("[!] No intelligence files found. Run collector.py first.")