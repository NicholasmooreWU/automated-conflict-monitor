import os
import pytest
from collector import IntelCollector

def test_fetch_intel_live_middle_east():
    api_key = os.getenv("NEWSAPI_KEY") or os.getenv("API_KEY")
    if not api_key:
        pytest.skip("No NewsAPI key set in environment variable NEWSAPI_KEY or API_KEY")
    collector = IntelCollector(api_key)
    articles = collector.fetch_intel("Middle East")
    assert isinstance(articles, list)
    # Should get at least one article if NewsAPI is working and not rate-limited
    assert len(articles) > 0, "No articles returned for 'Middle East' without date filter"
