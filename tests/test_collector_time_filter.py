import pytest
from collector import IntelCollector
from unittest.mock import patch

def test_fetch_intel_with_dates():
    collector = IntelCollector("test_api_key")
    with patch('collector.requests.get') as mock_get:
        mock_response = mock_get.return_value
        mock_response.json.return_value = {'totalResults': 1, 'articles': [{'title': 'Test', 'publishedAt': '2026-04-01'}]}
        mock_response.raise_for_status = lambda: None
        articles = collector.fetch_intel("test topic", from_date="2026-04-01", to_date="2026-04-02")
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test'
        # Ensure correct params
        params = mock_get.call_args[1]['params']
        assert params['from'] == "2026-04-01"
        assert params['to'] == "2026-04-02"

def test_fetch_intel_without_dates():
    collector = IntelCollector("test_api_key")
    with patch('collector.requests.get') as mock_get:
        mock_response = mock_get.return_value
        mock_response.json.return_value = {'totalResults': 1, 'articles': [{'title': 'Test'}]}
        mock_response.raise_for_status = lambda: None
        articles = collector.fetch_intel("test topic")
        assert len(articles) == 1
        assert articles[0]['title'] == 'Test'
        params = mock_get.call_args[1]['params']
        assert 'from' not in params
        assert 'to' not in params
