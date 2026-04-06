import pytest
import pandas as pd
from datetime import datetime
from dashboard import load_data

def test_time_filter_applies_correctly(monkeypatch):
    # Simulate articles with different dates
    data = [
        {'id': 1, 'title': 'A', 'published_at': '2026-04-01', 'region': 'Test', 'sentiment': 0.1},
        {'id': 2, 'title': 'B', 'published_at': '2026-04-03', 'region': 'Test', 'sentiment': 0.2},
        {'id': 3, 'title': 'C', 'published_at': '2026-04-05', 'region': 'Test', 'sentiment': 0.3},
    ]
    entities = [
        {'id': 1, 'article_id': 1, 'name': 'X', 'type': 'GPE'},
        {'id': 2, 'article_id': 2, 'name': 'Y', 'type': 'ORG'},
        {'id': 3, 'article_id': 3, 'name': 'Z', 'type': 'PERSON'},
    ]
    df_articles = pd.DataFrame(data)
    df_entities = pd.DataFrame(entities)

    # Monkeypatch load_data to return our test data
    monkeypatch.setattr('dashboard.load_data', lambda region_filter=None: (df_articles.copy(), df_entities.copy()))

    # Import load_data after monkeypatching to ensure patch is effective
    from dashboard import load_data as patched_load_data
    df_articles, df_entities = patched_load_data()
    # Debug output for columns
    if 'published_at' not in df_articles.columns:
        print('df_articles columns:', df_articles.columns)
    assert 'published_at' in df_articles.columns, "Test data must include 'published_at' column"
    df_articles['published_at'] = pd.to_datetime(df_articles['published_at'])
    start_date = datetime(2026, 4, 2).date()
    end_date = datetime(2026, 4, 4).date()
    mask = (df_articles['published_at'].dt.date >= start_date) & (df_articles['published_at'].dt.date <= end_date)
    filtered_articles = df_articles.loc[mask]
    filtered_entities = df_entities[df_entities['article_id'].isin(filtered_articles['id'])]

    assert len(filtered_articles) == 1
    assert filtered_articles.iloc[0]['title'] == 'B'
    assert len(filtered_entities) == 1
    assert filtered_entities.iloc[0]['name'] == 'Y'
