import pandas as pd
from datetime import datetime
from dashboard_utils import filter_articles_by_date

def test_filter_articles_by_date():
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
    df_articles['published_at'] = pd.to_datetime(df_articles['published_at'])
    df_entities = pd.DataFrame(entities)

    start_date = datetime(2026, 4, 2).date()
    end_date = datetime(2026, 4, 4).date()
    filtered_articles, filtered_entities = filter_articles_by_date(df_articles, df_entities, (start_date, end_date))

    assert len(filtered_articles) == 1
    assert filtered_articles.iloc[0]['title'] == 'B'
    assert len(filtered_entities) == 1
    assert filtered_entities.iloc[0]['name'] == 'Y'
