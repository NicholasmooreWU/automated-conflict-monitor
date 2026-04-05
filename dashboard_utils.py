import pandas as pd
from typing import Optional, Tuple

def filter_articles_by_date(df_articles: pd.DataFrame, df_entities: pd.DataFrame, date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]]):
    """
    Filter articles and entities by a date range (inclusive).
    Returns filtered (df_articles, df_entities).
    """
    if date_range and 'published_at' in df_articles.columns:
        start_date, end_date = date_range
        mask = (df_articles['published_at'].dt.date >= start_date) & (df_articles['published_at'].dt.date <= end_date)
        filtered_articles = df_articles.loc[mask]
        if not filtered_articles.empty and not df_entities.empty:
            article_ids = filtered_articles['id'].tolist()
            filtered_entities = df_entities[df_entities['article_id'].isin(article_ids)]
        else:
            filtered_entities = df_entities.iloc[0:0]
        return filtered_articles, filtered_entities
    return df_articles, df_entities
