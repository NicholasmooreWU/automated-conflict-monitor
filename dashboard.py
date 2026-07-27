# --- SOURCE CREDIBILITY TIERS ---
SOURCE_TIERS = {
    # Tier 1 - Primary intelligence value
    "reuters": 1.0,
    "bbc news": 1.0,
    "the atlantic": 0.9,
    "the new yorker": 0.9,
    "financial times": 1.0,
    # Tier 2 - Secondary value
    "business insider": 0.6,
    "yahoo entertainment": 0.5,
    "npr": 0.8,
    # Tier 3 - Minimal analytical value
    "kotaku": 0.1,
    "macrumors": 0.1,
    "hackaday": 0.2,
    "gizmodo": 0.2
}


import sqlite3
import pandas as pd
import networkx as nx
from pyvis.network import Network
import os
import sys
import traceback
import uuid
import re
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import relevance

# --- PER-REGION AUTO-PASS KEYWORDS ---
# Every region gets the same auto-pass privilege that used to belong only
# to China (see CHINA_DIRECT_MENTION in the old version of this file). A
# region with no entry here still gets scored by relevance.score_article's
# general keyword categories, just without a dedicated auto-pass list.
REGION_PRIORITY_KEYWORDS = {
    "Middle East": [
        "israel", "iran", "gaza", "hamas", "hezbollah", "idf", "west bank",
        "lebanon", "syria", "yemen", "houthi", "saudi arabia", "netanyahu",
    ],
    "South China Sea": [
        "china", "chinese", "beijing", "shanghai", "xi jinping", "ccp",
        "prc", "people's republic", "taiwan", "hong kong", "xinjiang",
        "tibet", "south china sea", "pla ", "politburo", "xinhua",
        "one china", "reunification",
    ],
    "Ukraine": [
        "ukraine", "russia", "russian", "putin", "zelensky", "kyiv",
        "moscow", "donbas", "crimea", "nato",
    ],
    "North Korea": [
        "north korea", "dprk", "kim jong un", "pyongyang", "missile test",
        "nuclear test", "denuclearization",
    ],
    "Syria": [
        "syria", "syrian", "assad", "damascus", "idlib", "kurdish forces",
        "sdf",
    ],
    "Yemen": [
        "yemen", "houthi", "sanaa", "saudi-led coalition", "red sea",
        "bab el-mandeb",
    ],
    "Horn of Africa": [
        "ethiopia", "somalia", "sudan", "eritrea", "tigray", "al-shabaab",
        "addis ababa",
    ],
    "Sahel Region": [
        "mali", "niger", "burkina faso", "sahel", "wagner group", "junta",
        "jihadist",
    ],
    "Kashmir": [
        "kashmir", "india", "pakistan", "line of control", "srinagar",
        "islamabad", "new delhi",
    ],
    "Myanmar": [
        "myanmar", "burma", "tatmadaw", "min aung hlaing", "rohingya",
        "naypyidaw",
    ],
}


def safe_str(val):
    return val if isinstance(val, str) else ""


def ensure_filtered_articles_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS filtered_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            body TEXT,
            relevance_score REAL,
            filter_reason TEXT
        )
    """)
    conn.commit()


def write_article_with_filter(conn, article, relevance_score, filter_reason):
    ensure_filtered_articles_table(conn)
    conn.execute(
        "INSERT INTO filtered_articles (title, body, relevance_score, filter_reason) VALUES (?, ?, ?, ?)",
        (article.get('title', ''), article.get('description', ''), relevance_score, filter_reason)
    )
    conn.commit()



# Load environment variables (safe at module level)
load_dotenv()

# --- PREDEFINED REGIONS ---
REGIONS = {
    "Middle East": "Middle East conflict Israel Iran Gaza",
    "South China Sea": "South China Sea Taiwan military tensions",
    "Ukraine": "Ukraine Russia war conflict",
    "North Korea": "North Korea DPRK missile nuclear",
    "Syria": "Syria conflict war Assad",
    "Yemen": "Yemen Houthi conflict Saudi",
    "Horn of Africa": "Ethiopia Somalia Sudan conflict",
    "Sahel Region": "Mali Niger Burkina Faso terrorism",
    "Kashmir": "Kashmir India Pakistan conflict",
    "Myanmar": "Myanmar Burma military coup"
}

# --- DATABASE CONNECTION ---
def load_data(region_filter=None):
    """Load data from database with error handling"""
    if not os.path.exists("intel_graph.db"):
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        conn = sqlite3.connect("intel_graph.db")
        
        if region_filter and region_filter != "All Regions":
            # Get Articles for specific region
            df_articles = pd.read_sql("SELECT * FROM articles WHERE region = ?", conn, params=(region_filter,))
            # Get Entities for those articles
            if not df_articles.empty:
                article_ids = df_articles['id'].tolist()
                placeholders = ','.join('?' * len(article_ids))
                df_entities = pd.read_sql(f"SELECT * FROM entities WHERE article_id IN ({placeholders})", conn, params=article_ids)
            else:
                df_entities = pd.DataFrame()
        else:
            # Get all data
            df_articles = pd.read_sql("SELECT * FROM articles", conn)
            df_entities = pd.read_sql("SELECT * FROM entities", conn)
        
        conn.close()
        # Ensure published_at is always datetime if present
        if 'published_at' in df_articles.columns:
            df_articles['published_at'] = pd.to_datetime(df_articles['published_at'], errors='coerce')
        return df_articles, df_entities
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def get_available_regions():
    """Get list of regions currently in the database"""
    if not os.path.exists("intel_graph.db"):
        return []
    
    try:
        conn = sqlite3.connect("intel_graph.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT region FROM articles WHERE region IS NOT NULL ORDER BY region")
        regions = [row[0] for row in cursor.fetchall()]
        conn.close()
        return regions
    except Exception as e:
        return []

# --- INTELLIGENCE COLLECTION PIPELINE ---
def run_intelligence_pipeline(region_name, search_query, max_articles=None, from_date=None, to_date=None):
    """
    Runs the complete intelligence pipeline: Collect -> Analyze -> Archive
    """

    try:
        from collector import IntelCollector
        from analyst import IntelAnalyst
        from archivist import IntelArchivist
        API_KEY = None
        try:
            API_KEY = st.secrets.get("API_KEY")
        except:
            API_KEY = os.getenv("API_KEY")
        if not API_KEY:
            return False, "⚠️ API_KEY not configured. Dashboard owner: Add API_KEY to Streamlit Cloud secrets."
        with st.spinner(f"Collecting intelligence on {region_name}..."):
            collector = IntelCollector(API_KEY)
            articles = collector.fetch_intel(search_query, from_date=from_date, to_date=to_date)
            if not articles:
                return False, "No articles found"
            collector.save_raw_intel(articles, region_name)
        # --- RELEVANCE FILTERING ---
        priority_keywords = REGION_PRIORITY_KEYWORDS.get(region_name)
        filtered_articles = []
        relevant_articles = []
        for art in articles:
            title = art.get('title', '')
            body = art.get('description', '')
            source = art.get('source', {})
            if isinstance(source, dict):
                source = source.get('name', '')
            score, reason = relevance.score_article(
                title, body, source=source,
                priority_keywords=priority_keywords,
                main_keyword=search_query,
            )
            art['relevance_score'] = score
            art['filter_reason'] = reason
            if relevance.is_relevant(reason):
                relevant_articles.append(art)
            else:
                filtered_articles.append(art)
        # Write filtered articles to DB
        conn = sqlite3.connect("intel_graph.db")
        ensure_filtered_articles_table(conn)
        conn.execute("DELETE FROM filtered_articles")
        for art in filtered_articles:
            write_article_with_filter(conn, art, art['relevance_score'], art['filter_reason'])
        conn.commit()
        conn.close()
        # Only process relevant articles
        with st.spinner(f"Analyzing {len(relevant_articles)} relevant articles with NLP..."):
            analyst = IntelAnalyst()
            if max_articles is None:
                raw_data = relevant_articles
            else:
                raw_data = relevant_articles[:max_articles]
            structured_intel = analyst.process_batch(
                raw_data, main_keyword=search_query, priority_keywords=priority_keywords
            )
            analyst.save_processed_intel(structured_intel)
        with st.spinner(f"💾 Archiving to database..."):
            archivist = IntelArchivist()
            archivist.connect()
            archivist.create_schema()
            archivist.ingest_data("processed_intel.json", region=region_name)
            archivist.close()

        return True, f"Successfully collected and analyzed {len(structured_intel)} articles (filtered {len(filtered_articles)} by new logic)"
    except Exception as e:
        return False, f"Error: {str(e)}"

# --- REPROCESS ALL ARTICLES IN DB WITH NEW FILTER ---
def reprocess_all_articles():
    conn = sqlite3.connect("intel_graph.db")
    ensure_filtered_articles_table(conn)
    conn.execute("DELETE FROM filtered_articles")
    df = pd.read_sql_query("SELECT * FROM articles", conn)
    pass_count = 0
    auto_pass = 0
    scored_pass = 0
    fail_count = 0
    reject_sports = 0
    reject_consumer = 0
    reject_health = 0
    fail_secondary = 0
    for _, row in df.iterrows():
        title = row.get('title', '')
        body = row.get('summary', '') or ''
        source = row.get('source', '')
        region = row.get('region', '')
        priority_keywords = REGION_PRIORITY_KEYWORDS.get(region)
        main_keyword = REGIONS.get(region)
        score, reason = relevance.score_article(
            title, body, source=source,
            priority_keywords=priority_keywords,
            main_keyword=main_keyword,
        )
        if relevance.is_relevant(reason):
            pass_count += 1
            if reason in ("priority_topic_mention", "main_keyword_match"):
                auto_pass += 1
            else:
                scored_pass += 1
        else:
            fail_count += 1
            if reason == "auto_reject_sports":
                reject_sports += 1
            elif reason == "auto_reject_consumer":
                reject_consumer += 1
            elif reason == "auto_reject_health":
                reject_health += 1
            elif reason == "failed_secondary_scoring":
                fail_secondary += 1
            write_article_with_filter(conn, row, score, reason)
    conn.commit()
    conn.close()
    return {
        "total": len(df),
        "pass_count": pass_count,
        "auto_pass": auto_pass,
        "scored_pass": scored_pass,
        "fail_count": fail_count,
        "reject_sports": reject_sports,
        "reject_consumer": reject_consumer,
        "reject_health": reject_health,
        "fail_secondary": fail_secondary
    }

# --- GRAPH BUILDER ---
def create_network_graph(df_entities, entity_type_filter=None, session_id=None):
    """
    Builds a network where Nodes = Entities and Edges = Co-occurrence in an article.
    Returns HTML content directly instead of saving to file to prevent cross-user interference.
    """
    if df_entities.empty:
        return None

    # Filter by entity type if specified
    if entity_type_filter and entity_type_filter != "All Types":
        df_entities = df_entities[df_entities['type'] == entity_type_filter]

    G = nx.Graph()

    # Need article_id -> source mapping for weighting
    # Load articles table for source info
    conn = sqlite3.connect("intel_graph.db")
    df_articles = pd.read_sql("SELECT id, source FROM articles", conn)
    conn.close()
    article_source_map = df_articles.set_index('id')['source'].to_dict()

    # Group entities by article to find connections
    article_groups = df_entities.groupby('article_id')['name'].apply(list)

    # Color mapping for entity types
    type_colors = {
        'GPE': '#ff6b6b',      # Red for countries/locations
        'ORG': '#4ecdc4',      # Teal for organizations
        'PERSON': '#45b7d1',   # Blue for people
        'NORP': '#f9ca24'      # Yellow for nationalities
    }

    for article_id, entities in article_groups.items():
        # Get source for this article
        source_name = article_source_map.get(article_id, "unknown").lower()
        weight = SOURCE_TIERS.get(source_name, 0.5)  # Default to 0.5 if unknown
        # Always create nodes, even if only one entity in article
        for entity in entities:
            if entity not in G.nodes():
                entity_type = df_entities[df_entities['name'] == entity]['type'].iloc[0]
                color = type_colors.get(entity_type, '#97c2fc')
                G.add_node(entity, title=f"{entity} ({entity_type})", color=color, entity_type=entity_type)
        # Only create edges if more than one entity
        if len(entities) < 2:
            continue
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                source = entities[i]
                target = entities[j]
                if G.has_edge(source, target):
                    G[source][target]['weight'] += weight
                else:
                    G.add_edge(source, target, weight=weight)

    if len(G.nodes()) == 0:
        return None

    # PyVis Visualization
    net = Network(height="650px", width="100%", bgcolor="#1e1e1e", font_color="white")
    net.from_nx(G)

    # Improved physics options for large graphs
    net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=100, spring_strength=0.08)
    net.show_buttons(filter_=['physics'])

    # Generate HTML content directly without saving to file
    # This prevents any cross-user file conflicts
    try:
        # PyVis generates HTML - we'll capture it as a string
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
            temp_file = f.name
        net.save_graph(temp_file)

        with open(temp_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Clean up temp file immediately
        os.unlink(temp_file)

        return html_content
    except Exception as e:
        print(f"ERROR generating graph: {e}")
        return None

# --- DATABASE INITIALIZATION ---
def init_database():
    """Initialize database if it doesn't exist"""
    try:
        if not os.path.exists("intel_graph.db"):
            conn = sqlite3.connect("intel_graph.db")
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE,
                    source TEXT,
                    published_at TEXT,
                    sentiment REAL,
                    summary TEXT,
                    region TEXT
                )
            ''')
            
            # Create entities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    name TEXT,
                    type TEXT,
                    FOREIGN KEY(article_id) REFERENCES articles(id)
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        return False

def clear_database():
    """Clear all data from the database (DANGER!)"""
    try:
        if not os.path.exists("intel_graph.db"):
            return True, "No database to clear"
        
        conn = sqlite3.connect("intel_graph.db")
        cursor = conn.cursor()
        
        # Delete all data from tables
        cursor.execute("DELETE FROM entities")
        cursor.execute("DELETE FROM articles")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='entities'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='articles'")
        
        conn.commit()
        conn.close()
        
        return True, "✅ All intelligence data cleared successfully"
    except Exception as e:
        return False, f"❌ Error clearing database: {str(e)}"

def cleanup_old_graphs(max_age_hours=24):
    """
    Clean up old graph HTML files from previous versions.
    New version generates graphs in-memory only, but this cleans up legacy files.
    """
    try:
        import time
        import glob
        
        current_time = time.time()
        graph_files = glob.glob("network*.html")  # All network HTML files
        
        deleted_count = 0
        for filepath in graph_files:
            try:
                # Check file age
                file_age_hours = (current_time - os.path.getmtime(filepath)) / 3600
                if file_age_hours > max_age_hours:
                    os.remove(filepath)
                    deleted_count += 1
            except:
                pass  # Skip files that can't be deleted
        
        if deleted_count > 0:
            print(f"CLEANUP: Removed {deleted_count} old graph files")
        return deleted_count
    except Exception as e:
        print(f"CLEANUP ERROR: {str(e)}")
        return 0

# --- DASHBOARD LAYOUT ---
def main():
    # Initialize session state for clean user sessions
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.region_filter = "All Regions"
        st.session_state.entity_type = "All Types"
        st.session_state.search_term = ""
        st.session_state.show_welcome = True
        # Create truly unique session ID using UUID
        st.session_state.session_id = str(uuid.uuid4())
        # Reset connections for this session (network graph starts empty)
        st.session_state.connections = []
        # Session initialized
    try:
        # Set page config (must be first Streamlit command)
        st.set_page_config(page_title="Conflict Monitor", layout="wide")
        # Initialize database on first run
        init_database()
        # Clean up old graph files (run once per app restart)
        if not hasattr(st.session_state, '_cleanup_done'):
            cleanup_old_graphs(max_age_hours=24)
            st.session_state._cleanup_done = True
        st.title("Automated Conflict Intelligence Monitor")
        st.markdown("Real-time OSINT & Network Analysis Dashboard")
        
        # ...existing code...
        
        # === SIDEBAR: INTELLIGENCE COLLECTION ===
        st.sidebar.header("Intelligence Collection")
        
        # Check API key availability
        api_key_available = False
        try:
            api_key_available = bool(st.secrets.get("API_KEY"))
        except:
            api_key_available = bool(os.getenv("API_KEY"))
        
        if not api_key_available:
            st.sidebar.warning("API Key not configured. Data collection disabled.")
            st.sidebar.info("Viewing Mode: Browse existing intelligence data below.")
        

        # --- KEYWORD SEARCH & COLLECTION ---
        st.sidebar.markdown("**Keyword Search**")
        keyword_query = st.sidebar.text_input("Enter keyword(s) (e.g. 'China', 'Ukraine')", value="China", key="keyword_search")
        
        # --- TIME FILTER FOR COLLECTION ---
        st.sidebar.markdown("**Collection Time Range**")
        col_from, col_to = st.sidebar.columns(2)
        with col_from:
            collect_from = st.date_input("From", key="collect_from")
        with col_to:
            collect_to = st.date_input("To", key="collect_to")

        # Collect Intelligence Button
        if st.sidebar.button("Collect Fresh Intelligence", type="primary", disabled=not api_key_available):
            from_date = str(collect_from) if collect_from else None
            to_date = str(collect_to) if collect_to else None
            # Check if date range is within the past month
            import datetime
            today = datetime.date.today()
            one_month_ago = today - datetime.timedelta(days=31)
            if (collect_from and collect_from < one_month_ago) or (collect_to and collect_to > today):
                st.sidebar.error("⚠️ Please select a date range within the past month. Data collection only supports the last 31 days.")
            else:
                # Use keyword_query for search, region for tagging only
                region_tag = keyword_query.strip().title() if keyword_query.strip() else "Unknown"
                # Pass None for max_articles to analyze all
                success, message = run_intelligence_pipeline(region_tag, keyword_query, None, from_date, to_date)
                if success:
                    st.sidebar.success(message)
                    st.rerun()
                else:
                    st.sidebar.error(message)

            st.sidebar.divider()
        
        # === SIDEBAR: DATA FILTERING ===
        st.sidebar.header("Data Filters")
        # Toggle for filtered articles
        show_filtered = st.sidebar.checkbox("Show filtered articles")
        # Reset button for clean view
        col1, col2 = st.sidebar.columns([3, 1])
        with col2:
            if st.button("Reset", help="Reset all filters to default", key="reset_filters_btn"):
                st.session_state.region_filter = "All Regions"
                st.session_state.entity_type = "All Types"
                st.session_state.search_term = ""
                st.rerun()
        with col1:
            st.markdown("**View Options**")
        # Get available regions from database
        available_regions = get_available_regions()
        if available_regions:
            # Use session state to persist selection
            default_index = 0
            if st.session_state.region_filter in available_regions:
                default_index = (["All Regions"] + available_regions).index(st.session_state.region_filter)
            region_filter = st.sidebar.selectbox(
                "View Data From:",
                options=["All Regions"] + available_regions,
                index=default_index,
                key="region_select"
            )
            st.session_state.region_filter = region_filter
        else:
            region_filter = None
            st.sidebar.warning("No data in database. Collect intelligence first!")
        # Entity type filter with session state
        entity_type_options = ["All Types", "GPE", "ORG", "PERSON", "NORP"]
        entity_default_index = entity_type_options.index(st.session_state.entity_type) if st.session_state.entity_type in entity_type_options else 0
        entity_type = st.sidebar.selectbox(
            "Filter Entity Type:",
            options=entity_type_options,
            index=entity_default_index,
            help="GPE: Countries/Cities, ORG: Organizations, PERSON: People, NORP: Nationalities",
            key="entity_select"
        )
        st.session_state.entity_type = entity_type
        st.sidebar.divider()
        
        # === LOAD DATA ===
        # If a keyword is set, filter articles/entities by keyword in title, description, or region
        def filter_by_keyword(df, keyword):
            if df.empty or not keyword:
                return df
            keyword_lower = keyword.lower()
            # Ensure columns are string type before .str operations
            title_col = df['title'].astype(str).str.lower()
            desc_col = df['description'].astype(str).str.lower() if 'description' in df.columns else pd.Series([""]*len(df))
            region_col = df['region'].astype(str).str.lower() if 'region' in df.columns else pd.Series([""]*len(df))
            mask = (
                title_col.str.contains(keyword_lower, na=False)
                | desc_col.str.contains(keyword_lower, na=False)
                | region_col.str.contains(keyword_lower, na=False)
            )
            return df[mask]

        df_articles, df_entities = load_data(None)  # Load all data
        keyword = st.session_state.get('keyword_search', '').strip()
        if keyword:
            df_articles = filter_by_keyword(df_articles, keyword)
            if not df_articles.empty:
                article_ids = df_articles['id'].tolist()
                df_entities = df_entities[df_entities['article_id'].isin(article_ids)]
            else:
                df_entities = pd.DataFrame()

        # --- SHOW FILTERED ARTICLES IF TOGGLED ---
        if show_filtered:
            conn = sqlite3.connect("intel_graph.db")
            try:
                filtered_df = pd.read_sql_query("SELECT * FROM filtered_articles", conn)
                st.info("Filtered Articles (Low Relevance):")
                st.dataframe(filtered_df, width='stretch', height=400)
            except Exception as e:
                st.warning(f"No filtered articles found or error: {e}")
            conn.close()
            st.stop()

        if df_articles.empty:
            st.warning("No intelligence data available. Use the sidebar to collect fresh intelligence!")
            st.info("**Getting Started:** Select a region above and click 'Collect Fresh Intelligence' to begin monitoring.")
            return
        
        # === SIDEBAR: DANGER ZONE ===
        with st.sidebar.expander("Danger Zone", expanded=False):
            st.warning("Clear All Data: This will permanently delete all collected intelligence from the database.")
            
            # Confirmation checkbox
            confirm_clear = st.checkbox("I understand this cannot be undone", key="confirm_clear")
            
            # Clear button (only enabled if confirmed)
            if st.button(
                "Clear All Data",
                type="secondary",
                disabled=not confirm_clear,
                help="Delete all articles and entities from database",
                key="clear_all_data_btn"
            ):
                success, message = clear_database()
                if success:
                    st.success(message)
                    # Reset session state
                    st.session_state.region_filter = "All Regions"
                    st.session_state.entity_type = "All Types"
                    st.session_state.search_term = ""
                    st.rerun()
                else:
                    st.error(message)
        
        # === MAIN AREA: TABS ===
        tab1, tab2, tab3, tab4 = st.tabs(["Network Graph", "Analytics", "Articles", "About"])
        
        # TAB 1: NETWORK GRAPH
        with tab1:
            st.subheader("Entity Relationship Network")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("Legend: Red = Countries/Locations, Blue = People, Green = Organizations, Yellow = Nationalities")
            with col2:
                if not df_entities.empty:
                    st.metric("Connections", len(df_entities))
            
            if not df_entities.empty:
                # Generate graph HTML content directly (no file saving)
                session_id = st.session_state.get('session_id', None)
                graph_html_content = create_network_graph(df_entities, entity_type, session_id)
                if graph_html_content:
                    # Render the graph directly from HTML content
                    components.html(graph_html_content, height=680, scrolling=False)
                else:
                    if df_entities['name'].nunique() > 0:
                        st.info("No connections found between entities. Try adjusting your filters or collecting more data.")
                    else:
                        st.warning("No entities found in the selected data.")
            else:
                st.warning("No entities found in the selected data.")
        
        # TAB 2: ANALYTICS
        with tab2:
            st.subheader("Intelligence Analytics")
            
            if not df_entities.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("Top 15 Mentioned Entities")
                    top_entities = df_entities['name'].value_counts().head(15)
                    st.bar_chart(top_entities)
                
                with col2:
                    st.markdown("Entity Type Distribution")
                    entity_type_dist = df_entities['type'].value_counts()
                    st.bar_chart(entity_type_dist)
                
                # Sentiment over time
                if 'published_at' in df_articles.columns:
                    st.markdown("Sentiment Trend Over Time")
                    df_articles['published_date'] = pd.to_datetime(df_articles['published_at']).dt.date
                    sentiment_trend = df_articles.groupby('published_date')['sentiment'].mean()
                    st.line_chart(sentiment_trend)
                
                # Top entity pairs (co-occurrences)
                st.markdown("Top Entity Connections")
                entity_pairs = []
                article_groups = df_entities.groupby('article_id')['name'].apply(list)
                for entities in article_groups:
                    for i in range(len(entities)):
                        for j in range(i + 1, len(entities)):
                            entity_pairs.append(tuple(sorted([entities[i], entities[j]])))
                
                if entity_pairs:
                    pair_counts = pd.Series(entity_pairs).value_counts().head(10)
                    pair_df = pd.DataFrame({
                        'Entity Pair': [f"{p[0]} ↔ {p[1]}" for p in pair_counts.index],
                        'Co-occurrences': pair_counts.values
                    })
                    st.dataframe(pair_df, width='stretch')
            else:
                st.info("No entity data available for analysis.")
        
        # TAB 3: ARTICLES TABLE
        with tab3:
            st.subheader("Intelligence Reports")
            
            # Search functionality with session state
            search_term = st.text_input(
                "Search articles by title", 
                value=st.session_state.search_term,
                key="article_search"
            )
            st.session_state.search_term = search_term
            
            display_df = df_articles.copy()
            if search_term:
                display_df = display_df[display_df['title'].str.contains(search_term, case=False, na=False)]
            
            # Sort options
            sort_by = st.selectbox("Sort by:", ["published_at", "sentiment", "source"])
            display_df = display_df.sort_values(by=sort_by, ascending=False)
            
            # Display columns
            cols_to_show = ['title', 'source', 'sentiment', 'published_at']
            if 'region' in display_df.columns:
                cols_to_show.append('region')
            
            st.dataframe(
                display_df[cols_to_show],
                width='stretch',
                height=500
            )
            
            # Export option
            if st.button("Export to CSV", key="export_csv_btn"):
                csv = display_df[cols_to_show].to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"intel_report_{(region_filter or 'AllRegions').replace(' ', '')}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

        # TAB 4: ABOUT
        with tab4:
            st.subheader("About This System")
            st.markdown("""
Mission

This automated OSINT (Open Source Intelligence) system monitors global conflicts by:
- Collecting real-time news from multiple sources
- Analyzing text with NLP (Named Entity Recognition & Sentiment Analysis)
- Archiving structured intelligence in a relational database
- Visualizing entity relationships to reveal hidden patterns

Technology Stack
- NLP: spaCy (Entity Recognition), VADER (Sentiment)
- Data: NewsAPI, SQLite, pandas
- Visualization: NetworkX, PyVis, Streamlit
- Security: Environment variables, input sanitization

Entity Types
- GPE: Geopolitical Entities (countries, cities)
- ORG: Organizations (militaries, governments, NGOs)
- PERSON: Key individuals (leaders, officials)
- NORP: Nationalities or religious/political groups

How to Use

For Public Users (Viewing Mode):
1. Browse pre-collected intelligence data from various regions
2. Explore the network graph to see entity relationships
3. Use filters to focus on specific regions or entity types
4. Export data to CSV for further analysis

For Dashboard Administrators:
1. Configure API_KEY in Streamlit Cloud secrets
2. Select a region and click "Collect Fresh Intelligence"
3. New data is automatically collected, analyzed, and archived
4. All users can then view the updated intelligence

Data Collection Access
- API Key Required: Fresh data collection requires a NewsAPI key
- Public Access: All users can view existing data without authentication
- Administrator: Configures API key to enable data collection

Limitations
- Data limited to publicly available news sources
- Sentiment analysis may not capture nuance
- Entity extraction depends on mention frequency
- Update frequency limited by API rate limits

Legal & Attribution
- Data Source: News data provided by [NewsAPI.org](https://newsapi.org)
- Usage: Educational and research purposes
- Disclaimer: This tool aggregates publicly available information for analysis. News content copyright belongs to original publishers.
- License: This software is licensed under MIT License
- No Warranty: Provided "as-is" without guarantees of accuracy or completeness

Attribution

Built with: spaCy, VADER, NetworkX, Streamlit, NewsAPI, SQLite
            """)
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            st.error(f"Fatal Error: {str(e)}")
            st.code(traceback.format_exc())
        except:
            pass
        raise