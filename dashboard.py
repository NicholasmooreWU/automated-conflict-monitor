import streamlit as st
import sqlite3
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="Conflict Monitor", layout="wide")

# --- DATABASE CONNECTION ---
def load_data():
    conn = sqlite3.connect("intel_graph.db")
    
    # Get Articles
    df_articles = pd.read_sql("SELECT * FROM articles", conn)
    
    # Get Entities
    df_entities = pd.read_sql("SELECT * FROM entities", conn)
    
    conn.close()
    return df_articles, df_entities

# --- GRAPH BUILDER ---
def create_network_graph(df_entities, min_connections=1):
    """
    Builds a network where Nodes = Entities and Edges = Co-occurrence in an article.
    """
    G = nx.Graph()
    
    # Group entities by article to find connections
    article_groups = df_entities.groupby('article_id')['name'].apply(list)
    
    for entities in article_groups:
        # Create nodes
        for entity in entities:
            G.add_node(entity, title=entity, color='#97c2fc')
            
        # Create edges (connect every entity in this article to every other entity)
        # This shows they are "linked" by this news story
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                source = entities[i]
                target = entities[j]
                
                if G.has_edge(source, target):
                    G[source][target]['weight'] += 1
                else:
                    G.add_edge(source, target, weight=1)

    # Filter out weak connections to keep graph clean
    # (Optional: Only show nodes with at least N connections)
    # G = nx.k_core(G, k=min_connections) 

    # PyVis Visualization
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    
    # Physics options for a cool floating effect
    net.force_atlas_2based()
    
    # Save to HTML file
    net.save_graph("network.html")
    return "network.html"

# --- DASHBOARD LAYOUT ---
def main():
    st.title("🕵️ Automated Conflict Intelligence Monitor")
    st.markdown("### Real-time OSINT & Network Analysis")
    
    # Load Data
    try:
        df_articles, df_entities = load_data()
    except Exception as e:
        st.error(f"Database error: {e}. Did you run archivist.py?")
        return

    # Sidebar Stats
    st.sidebar.header("Intel Summary")
    st.sidebar.metric("Total Articles Scanned", len(df_articles))
    st.sidebar.metric("Entities Detected", len(df_entities))
    st.sidebar.metric("Avg Sentiment", f"{df_articles['sentiment'].mean():.2f}")
    
    # Top Entities Chart
    st.sidebar.subheader("Top Mentioned Entities")
    top_entities = df_entities['name'].value_counts().head(10)
    st.sidebar.bar_chart(top_entities)

    # Main Area: Network Graph
    st.subheader("🔗 Entity Relationship Network")
    st.info("Nodes are People/Orgs/Locations. Lines indicate they appeared in the same intelligence report.")
    
    graph_html = create_network_graph(df_entities)
    
    # Render the HTML graph
    with open(graph_html, 'r', encoding='utf-8') as f:
        source_code = f.read() 
    components.html(source_code, height=610)

    # Data Table
    st.subheader("📄 Latest Intelligence Reports")
    st.dataframe(df_articles[['title', 'source', 'sentiment', 'published_at']])

if __name__ == "__main__":
    main()