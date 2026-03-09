import streamlit as st
import sqlite3
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
from collector import IntelCollector
from analyst import IntelAnalyst
from archivist import IntelArchivist

# --- CONFIGURATION ---
st.set_page_config(page_title="Conflict Monitor", layout="wide")

# Load environment variables
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

def get_available_regions():
    """Get list of regions currently in the database"""
    conn = sqlite3.connect("intel_graph.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT region FROM articles WHERE region IS NOT NULL ORDER BY region")
        regions = [row[0] for row in cursor.fetchall()]
        conn.close()
        return regions
    except:
        conn.close()
        return []

# --- INTELLIGENCE COLLECTION PIPELINE ---
def run_intelligence_pipeline(region_name, search_query, max_articles=20):
    """
    Runs the complete intelligence pipeline: Collect -> Analyze -> Archive
    """
    try:
        API_KEY = os.getenv("API_KEY")
        if not API_KEY:
            return False, "API_KEY not found in environment variables"
        
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
def create_network_graph(df_entities, entity_type_filter=None):
    """
    Builds a network where Nodes = Entities and Edges = Co-occurrence in an article.
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
    
    # Save to HTML file
    net.save_graph("network.html")
    return "network.html"

# --- DASHBOARD LAYOUT ---
def main():
    st.title("🕵️ Automated Conflict Intelligence Monitor")
    st.markdown("### Real-time OSINT & Network Analysis Dashboard")
    
    # === SIDEBAR: INTELLIGENCE COLLECTION ===
    st.sidebar.header("🔍 Intelligence Collection")
    
    # Region selector
    selected_region = st.sidebar.selectbox(
        "Select Region to Monitor",
        options=list(REGIONS.keys()),
        index=0
    )
    
    # Custom search query (advanced users)
    use_custom = st.sidebar.checkbox("⚙️ Use Custom Query", value=False)
    if use_custom:
        custom_query = st.sidebar.text_input("Custom Search Terms", value=REGIONS[selected_region])
        max_articles = st.sidebar.slider("Max Articles to Analyze", 10, 50, 20)
    else:
        custom_query = REGIONS[selected_region]
        max_articles = 20
    
    # Collect Intelligence Button
    if st.sidebar.button("🚀 Collect Fresh Intelligence", type="primary"):
        success, message = run_intelligence_pipeline(selected_region, custom_query, max_articles)
        if success:
            st.sidebar.success(message)
            st.rerun()
        else:
            st.sidebar.error(message)
    
    st.sidebar.divider()
    
    # === SIDEBAR: DATA FILTERING ===
    st.sidebar.header("📊 Data Filters")
    
    # Get available regions from database
    available_regions = get_available_regions()
    
    if available_regions:
        region_filter = st.sidebar.selectbox(
            "View Data From:",
            options=["All Regions"] + available_regions,
            index=0
        )
    else:
        region_filter = None
        st.sidebar.warning("No data in database. Collect intelligence first!")
    
    # Entity type filter
    entity_type = st.sidebar.selectbox(
        "Filter Entity Type:",
        options=["All Types", "GPE", "ORG", "PERSON", "NORP"],
        help="GPE: Countries/Cities, ORG: Organizations, PERSON: People, NORP: Nationalities"
    )
    
    st.sidebar.divider()
    
    # === LOAD DATA ===
    try:
        df_articles, df_entities = load_data(region_filter if region_filter != "All Regions" else None)
    except Exception as e:
        st.error(f"Database error: {e}. Run the collection pipeline first!")
        return
    
    if df_articles.empty:
        st.warning("📭 No intelligence data available. Use the sidebar to collect fresh intelligence!")
        return
    
    # === SIDEBAR: STATISTICS ===
    st.sidebar.header("📈 Intel Summary")
    st.sidebar.metric("Total Articles", len(df_articles))
    st.sidebar.metric("Unique Entities", df_entities['name'].nunique() if not df_entities.empty else 0)
    st.sidebar.metric("Avg Sentiment", f"{df_articles['sentiment'].mean():.2f}" if 'sentiment' in df_articles.columns else "N/A")
    
    # Regional distribution
    if 'region' in df_articles.columns:
        st.sidebar.subheader("📍 Regional Coverage")
        region_counts = df_articles['region'].value_counts()
        st.sidebar.bar_chart(region_counts)
    
    # === MAIN AREA: TABS ===
    tab1, tab2, tab3, tab4 = st.tabs(["🔗 Network Graph", "📊 Analytics", "📄 Articles", "ℹ️ About"])
    
    # TAB 1: NETWORK GRAPH
    with tab1:
        st.subheader("🔗 Entity Relationship Network")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("**Legend:** 🔴 Countries/Locations  🔵 People  🟢 Organizations  🟡 Nationalities")
        with col2:
            if not df_entities.empty:
                st.metric("Connections", len(df_entities))
        
        if not df_entities.empty:
            graph_html = create_network_graph(df_entities, entity_type)
            
            if graph_html and os.path.exists(graph_html):
                with open(graph_html, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                components.html(source_code, height=680)
            else:
                st.warning("No entities to display with current filters.")
        else:
            st.warning("No entities found in the selected data.")
    
    # TAB 2: ANALYTICS
    with tab2:
        st.subheader("📊 Intelligence Analytics")
        
        if not df_entities.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Top 15 Mentioned Entities")
                top_entities = df_entities['name'].value_counts().head(15)
                st.bar_chart(top_entities)
            
            with col2:
                st.markdown("#### Entity Type Distribution")
                entity_type_dist = df_entities['type'].value_counts()
                st.bar_chart(entity_type_dist)
            
            # Sentiment over time
            if 'published_at' in df_articles.columns:
                st.markdown("#### Sentiment Trend Over Time")
                df_articles['published_date'] = pd.to_datetime(df_articles['published_at']).dt.date
                sentiment_trend = df_articles.groupby('published_date')['sentiment'].mean()
                st.line_chart(sentiment_trend)
            
            # Top entity pairs (co-occurrences)
            st.markdown("#### Top Entity Connections")
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
        st.subheader("📄 Intelligence Reports")
        
        # Search functionality
        search_term = st.text_input("🔍 Search articles by title", "")
        
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
        if st.button("📥 Export to CSV"):
            csv = display_df[cols_to_show].to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"intel_report_{selected_region}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    # TAB 4: ABOUT
    with tab4:
        st.subheader("ℹ️ About This System")
        st.markdown("""
        ### 🎯 Mission
        This automated OSINT (Open Source Intelligence) system monitors global conflicts by:
        - 📡 **Collecting** real-time news from multiple sources
        - 🧠 **Analyzing** text with NLP (Named Entity Recognition & Sentiment Analysis)
        - 🗄️ **Archiving** structured intelligence in a relational database
        - 🔗 **Visualizing** entity relationships to reveal hidden patterns
        
        ### 🛠️ Technology Stack
        - **NLP**: spaCy (Entity Recognition), VADER (Sentiment)
        - **Data**: NewsAPI, SQLite, pandas
        - **Visualization**: NetworkX, PyVis, Streamlit
        - **Security**: Environment variables, input sanitization
        
        ### 📚 Entity Types
        - **GPE**: Geopolitical Entities (countries, cities)
        - **ORG**: Organizations (militaries, governments, NGOs)
        - **PERSON**: Key individuals (leaders, officials)
        - **NORP**: Nationalities or religious/political groups
        
        ### 🚀 How to Use
        1. Select a region from the sidebar
        2. Click "Collect Fresh Intelligence" to gather latest data
        3. Explore the network graph to see entity relationships
        4. Use filters to focus on specific regions or entity types
        5. Compare multiple regions by selecting "All Regions"
        
        ### ⚠️ Limitations
        - Data limited to publicly available news sources
        - Sentiment analysis may not capture nuance
        - Entity extraction depends on mention frequency
        - Update frequency limited by API rate limits
        """)

if __name__ == "__main__":
    main()