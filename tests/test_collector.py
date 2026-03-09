"""
Unit tests for the IntelCollector module.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from collector import IntelCollector


class TestIntelCollector:
    """Test suite for IntelCollector class"""
    
    @pytest.fixture
    def collector(self):
        """Create a collector instance for testing"""
        return IntelCollector("test_api_key_123")
    
    def test_initialization(self, collector):
        """Test that the collector initializes correctly"""
        assert collector.api_key == "test_api_key_123"
        assert collector.base_url == "https://newsapi.org/v2/everything"
    
    def test_sanitize_filename_removes_dangerous_chars(self, collector):
        """Test that dangerous characters are removed from filenames"""
        dangerous = "../../../etc/passwd"
        result = collector._sanitize_filename(dangerous)
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result
    
    def test_sanitize_filename_removes_special_chars(self, collector):
        """Test that special characters are replaced"""
        special = "file<>:\"|?*name"
        result = collector._sanitize_filename(special)
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
    
    def test_sanitize_filename_limits_length(self, collector):
        """Test that filenames are limited to 100 characters"""
        long_name = "a" * 200
        result = collector._sanitize_filename(long_name)
        assert len(result) <= 100
    
    def test_sanitize_filename_handles_empty_string(self, collector):
        """Test that empty strings return 'unknown'"""
        result = collector._sanitize_filename("")
        assert result == "unknown"
    
    @patch('collector.requests.get')
    def test_fetch_intel_success(self, mock_get, collector):
        """Test successful intelligence fetching"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'totalResults': 100,
            'articles': [
                {'title': 'Test Article', 'description': 'Test content'}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test fetch
        result = collector.fetch_intel("test topic")
        
        # Assertions
        assert len(result) == 1
        assert result[0]['title'] == 'Test Article'
        mock_get.assert_called_once()
    
    @patch('collector.requests.get')
    def test_fetch_intel_handles_network_error(self, mock_get, collector):
        """Test that network errors are handled gracefully"""
        mock_get.side_effect = Exception("Network error")
        
        result = collector.fetch_intel("test topic")
        
        assert result == []
    
    @patch('collector.requests.get')
    def test_fetch_intel_handles_empty_response(self, mock_get, collector):
        """Test handling of empty API responses"""
        mock_response = Mock()
        mock_response.json.return_value = {'totalResults': 0, 'articles': []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = collector.fetch_intel("nonexistent topic")
        
        assert result == []
    
    @patch('collector.os.makedirs')
    @patch('builtins.open', create=True)
    @patch('collector.json.dump')
    def test_save_raw_intel(self, mock_json_dump, mock_open, mock_makedirs, collector):
        """Test saving intelligence data to file"""
        test_data = [{'title': 'Test', 'content': 'Test content'}]
        
        collector.save_raw_intel(test_data, "test_topic")
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with("intel_data", exist_ok=True)
        
        # Verify file operations
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once()
    
    def test_save_raw_intel_handles_empty_data(self, collector, capsys):
        """Test that empty data is not saved"""
        collector.save_raw_intel([], "test_topic")
        
        captured = capsys.readouterr()
        assert "[!] No data to save" in captured.out
    
    def test_api_key_in_request_params(self, collector):
        """Test that API key is included in request parameters"""
        with patch('collector.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'totalResults': 0, 'articles': []}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            collector.fetch_intel("test")
            
            # Check that API key was passed in params
            call_args = mock_get.call_args
            assert call_args[1]['params']['apiKey'] == "test_api_key_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
