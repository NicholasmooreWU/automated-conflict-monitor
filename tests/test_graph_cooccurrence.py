import sqlite3
import os
import pandas as pd
import pytest
from dashboard import load_data, create_network_graph

def setup_test_db():
    # Remove existing test db if present
    if os.path.exists('intel_graph.db'):
        os.remove('intel_graph.db')
    conn = sqlite3.connect('intel_graph.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            sentiment REAL,
            summary TEXT,
            region TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            name TEXT,
            type TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id)
        )
    ''')
    # Insert one article with two entities
    cursor.execute("INSERT INTO articles (title, source, published_at, sentiment, summary, region) VALUES (?, ?, ?, ?, ?, ?)",
                   ("Test Article", "Test Source", "2026-04-12T10:00:00Z", 0.5, "Test summary", "Test Region"))
    article_id = cursor.lastrowid
    cursor.execute("INSERT INTO entities (article_id, name, type) VALUES (?, ?, ?)", (article_id, "EntityA", "PERSON"))
    cursor.execute("INSERT INTO entities (article_id, name, type) VALUES (?, ?, ?)", (article_id, "EntityB", "ORG"))
    conn.commit()
    conn.close()

def test_graph_with_cooccurring_entities():
    setup_test_db()
    df_articles, df_entities = load_data()
    print("ARTICLES DF:\n", df_articles)
    print("ENTITIES DF:\n", df_entities)
    html = create_network_graph(df_entities)
    print("GRAPH HTML:\n", html)
    assert html is not None
    assert "EntityA" in html and "EntityB" in html
    # Should have at least one edge (connection)
    assert 'edges' in html or 'links' in html

if __name__ == "__main__":
    setup_test_db()
    test_graph_with_cooccurring_entities()
    print("Test passed: Graph renders with co-occurring entities.")
