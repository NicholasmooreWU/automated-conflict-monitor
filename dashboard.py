import streamlit as st
import sqlite3
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import sys
import traceback
import uuid
import sys
from dotenv import load_dotenv



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
def run_intelligence_pipeline(region_name, search_query, max_articles=20):
    """
    Runs the complete intelligence pipeline: Collect -> Analyze -> Archive
    """
    try:
        # Lazy import to avoid startup crashes
        from collector import IntelCollector
        from analyst import IntelAnalyst
        from archivist import IntelArchivist
        
        # Try Streamlit secrets first, then fall back to .env
        API_KEY = None
        try:
            API_KEY = st.secrets.get("API_KEY")
        except:
            API_KEY = os.getenv("API_KEY")
        
        if not API_KEY:
            return False, "⚠️ API_KEY not configured. Dashboard owner: Add API_KEY to Streamlit Cloud secrets."
        
        # Step 1: Collect
        with st.spinner(f"🔍 Collecting intelligence on {region_name}..."):
            collector = IntelCollector(API_KEY)
            articles = collector.fetch_intel(search_query)
            
            if not articles:
                return False, "No articles found"
            
            collector.save_raw_intel(articles, region_name)
        
        # Step 2: Analyze
        with st.spinner(f"🧠 Analyzing {len(articles[:max_articles])} articles with NLP..."):
            analyst = IntelAnalyst()
            raw_data = articles[:max_articles]  # Limit for performance
            structured_intel = analyst.process_batch(raw_data)
            analyst.save_processed_intel(structured_intel)
        
        # Step 3: Archive
        with st.spinner(f"💾 Archiving to database..."):
            archivist = IntelArchivist()
            archivist.connect()
            archivist.create_schema()
            archivist.ingest_data("processed_intel.json", region=region_name)
            archivist.close()
        
        return True, f"Successfully collected and analyzed {len(structured_intel)} articles"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

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
    
    # Group entities by article to find connections
    article_groups = df_entities.groupby('article_id')['name'].apply(list)
    
    # Color mapping for entity types
    type_colors = {
        'GPE': '#ff6b6b',      # Red for countries/locations
        'ORG': '#4ecdc4',      # Teal for organizations
        'PERSON': '#45b7d1',   # Blue for people
        'NORP': '#f9ca24'      # Yellow for nationalities
    }
    
    for entities in article_groups:
        if len(entities) < 2:
            continue
            
        # Create nodes with entity type info
        for entity in entities:
            if entity not in G.nodes():
                # Get entity type from dataframe
                entity_type = df_entities[df_entities['name'] == entity]['type'].iloc[0]
                color = type_colors.get(entity_type, '#97c2fc')
                G.add_node(entity, title=f"{entity} ({entity_type})", color=color, entity_type=entity_type)
            
        # Create edges
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                source = entities[i]
                target = entities[j]
                
                if G.has_edge(source, target):
                    G[source][target]['weight'] += 1
                else:
                    G.add_edge(source, target, weight=1)

    if len(G.nodes()) == 0:
        return None

    # PyVis Visualization
    net = Network(height="650px", width="100%", bgcolor="#1e1e1e", font_color="white")
    net.from_nx(G)
    
    # Enhanced physics options
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
        
        # Welcome message for new users (dismissible)
        if st.session_state.get('show_welcome', False):
            st.info("Welcome! Each user gets an independent view. Use filters to explore intelligence data, or reset anytime with the reset button.")
            if st.button("Got it!", key="got_it_btn"):
                st.session_state.show_welcome = False
                st.rerun()

        # --- SESSION-BASED CONNECT DATA ---
        st.markdown("Session-Specific Data Connection (No Login Required)")

        if 'user_data' not in st.session_state:
            st.session_state['user_data'] = None

        if st.button("Connect Data", key="connect_data_btn"):
            # Simulate loading data unique to this session
            st.session_state['user_data'] = f"Data for session {st.session_state.session_id}"

        if st.session_state['user_data']:
            st.success("Your Data:")
            st.write(st.session_state['user_data'])
        else:
            st.info("No data connected yet. Click the button above.")

        if st.button("Reset Session Data", key="reset_session_data_btn"):
            st.session_state['user_data'] = None
        
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
        
        # Region selector
        selected_region = st.sidebar.selectbox(
            "Select Region to Monitor",
            options=list(REGIONS.keys()),
            index=0
        )
        
        # Custom search query (advanced users)
        use_custom = st.sidebar.checkbox("Use Custom Query", value=False)
        if use_custom:
            custom_query = st.sidebar.text_input("Custom Search Terms", value=REGIONS[selected_region])
            max_articles = st.sidebar.slider("Max Articles to Analyze", 10, 50, 20)
        else:
            custom_query = REGIONS[selected_region]
            max_articles = 20
        
        # Collect Intelligence Button
        if st.sidebar.button("Collect Fresh Intelligence", type="primary", disabled=not api_key_available):
            success, message = run_intelligence_pipeline(selected_region, custom_query, max_articles)
            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)
        
            st.sidebar.divider()
        
        # === SIDEBAR: DATA FILTERING ===
        st.sidebar.header("Data Filters")
        
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
        df_articles, df_entities = load_data(region_filter if region_filter != "All Regions" else None)
        
        if df_articles.empty:
            st.warning("📭 No intelligence data available. Use the sidebar to collect fresh intelligence!")
            st.info("💡 **Getting Started:** Select a region above and click '🚀 Collect Fresh Intelligence' to begin monitoring.")
            return
        
        # === SIDEBAR: STATISTICS ===
        st.sidebar.header("Intel Summary")
        st.sidebar.metric("Total Articles", len(df_articles))
        st.sidebar.metric("Unique Entities", df_entities['name'].nunique() if not df_entities.empty else 0)
        st.sidebar.metric("Avg Sentiment", f"{df_articles['sentiment'].mean():.2f}" if 'sentiment' in df_articles.columns else "N/A")
        
        # Regional distribution
        if 'region' in df_articles.columns:
            st.sidebar.subheader("Regional Coverage")
            region_counts = df_articles['region'].value_counts()
            st.sidebar.bar_chart(region_counts)
        
        st.sidebar.divider()
        
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
                    st.warning("No entities to display with current filters.")
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
                    file_name=f"intel_report_{selected_region}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
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
                        - Disclaimer: This tool aggregates publicly available information for analysis.
                            News content copyright belongs to original publishers.
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

# --- SESSION-BASED CONNECT DATA ---
st.markdown("### Session-Specific Data Connection (No Login Required)")

if 'user_data' not in st.session_state:
    st.session_state['user_data'] = None

if st.button("Connect Data", key="connect_data_btn_bottom"):
    # Simulate loading data unique to this session
    st.session_state['user_data'] = f"Data for session {st.session_state.session_id}"

if st.session_state['user_data']:
    st.success("Your Data:")
    st.write(st.session_state['user_data'])
else:
    st.info("No data connected yet. Click the button above.")

if st.button("Reset Session Data", key="reset_session_data_btn_bottom"):
    st.session_state['user_data'] = None