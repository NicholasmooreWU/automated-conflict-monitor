"""
Unit tests for the IntelAnalyst module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from analyst import IntelAnalyst


class TestIntelAnalyst:
    """Test suite for IntelAnalyst class"""
    
    @pytest.fixture
    def analyst(self):
        """Create an analyst instance for testing"""
        with patch('analyst.spacy.load') as mock_spacy, \
             patch('analyst.SentimentIntensityAnalyzer') as mock_vader:
            mock_nlp = Mock()
            mock_spacy.return_value = mock_nlp
            mock_sentiment = Mock()
            mock_vader.return_value = mock_sentiment
            
            analyst_instance = IntelAnalyst()
            
            # Ensure mocks are accessible after initialization
            analyst_instance.nlp = mock_nlp
            analyst_instance.sentiment_analyzer = mock_sentiment
            
            yield analyst_instance
    
    @pytest.fixture
    def sample_article(self):
        """Sample article data for testing"""
        return {
            'title': 'Conflict in Middle East',
            'description': 'Rising tensions between nations',
            'source': {'name': 'Test News'},
            'publishedAt': '2026-03-09T10:00:00Z'
        }
    
    def test_initialization(self, analyst):
        """Test that the analyst initializes correctly"""
        assert analyst.nlp is not None
        assert analyst.sentiment_analyzer is not None
    
    def test_analyze_article_extracts_sentiment(self, analyst, sample_article):
        """Test sentiment score extraction"""
        analyst.sentiment_analyzer.polarity_scores = Mock(
            return_value={'compound': 0.5}
        )
        
        # Mock spaCy NER
        mock_doc = Mock()
        mock_doc.ents = []
        analyst.nlp = Mock(return_value=mock_doc)
        
        result = analyst.analyze_article(sample_article)
        
        assert 'sentiment' in result
        assert result['sentiment'] == 0.5
    
    def test_analyze_article_extracts_entities(self, analyst, sample_article):
        """Test entity extraction"""
        analyst.sentiment_analyzer.polarity_scores = Mock(
            return_value={'compound': 0.0}
        )
        
        # Mock spaCy entities
        mock_entity1 = Mock()
        mock_entity1.text = "Middle East"
        mock_entity1.label_ = "GPE"
        
        mock_entity2 = Mock()
        mock_entity2.text = "United Nations"
        mock_entity2.label_ = "ORG"
        
        mock_doc = Mock()
        mock_doc.ents = [mock_entity1, mock_entity2]
        analyst.nlp = Mock(return_value=mock_doc)
        
        result = analyst.analyze_article(sample_article)
        
        assert 'entities' in result
        assert len(result['entities']) == 2
        assert ('Middle East', 'GPE') in result['entities']
        assert ('United Nations', 'ORG') in result['entities']
    
    def test_analyze_article_filters_entity_types(self, analyst, sample_article):
        """Test that only target entity types are extracted"""
        analyst.sentiment_analyzer.polarity_scores = Mock(
            return_value={'compound': 0.0}
        )
        
        # Mock entities with mixed types
        valid_entity = Mock()
        valid_entity.text = "Iran"
        valid_entity.label_ = "GPE"
        
        invalid_entity = Mock()
        invalid_entity.text = "Yesterday"
        invalid_entity.label_ = "DATE"  # Should be filtered out
        
        mock_doc = Mock()
        mock_doc.ents = [valid_entity, invalid_entity]
        analyst.nlp = Mock(return_value=mock_doc)
        
        result = analyst.analyze_article(sample_article)
        
        # Only GPE entity should be in results
        assert len(result['entities']) == 1
        assert ('Iran', 'GPE') in result['entities']
    
    def test_analyze_article_removes_duplicate_entities(self, analyst, sample_article):
        """Test that duplicate entities are removed"""
        analyst.sentiment_analyzer.polarity_scores = Mock(
            return_value={'compound': 0.0}
        )
        
        # Mock duplicate entities
        entity1 = Mock()
        entity1.text = "China"
        entity1.label_ = "GPE"
        
        entity2 = Mock()
        entity2.text = "China"  # Duplicate
        entity2.label_ = "GPE"
        
        mock_doc = Mock()
        mock_doc.ents = [entity1, entity2]
        analyst.nlp = Mock(return_value=mock_doc)
        
        result = analyst.analyze_article(sample_article)
        
        # Should only have one China entity
        assert len(result['entities']) == 1
    
    def test_process_batch_skips_removed_articles(self, analyst):
        """Test that [Removed] articles are skipped"""
        articles = [
            {'title': '[Removed]', 'description': 'Removed', 
             'source': {'name': 'Test'}, 'publishedAt': '2026-03-09'},
            {'title': 'Valid Article', 'description': 'Content',
             'source': {'name': 'Test'}, 'publishedAt': '2026-03-09'}
        ]
        
        analyst.sentiment_analyzer.polarity_scores = Mock(
            return_value={'compound': 0.0}
        )
        mock_doc = Mock()
        mock_doc.ents = []
        analyst.nlp = Mock(return_value=mock_doc)
        
        result = analyst.process_batch(articles)
        
        # Only 1 article should be processed
        assert len(result) == 1
        assert result[0]['title'] == 'Valid Article'
    
    @patch('builtins.open', create=True)
    @patch('analyst.json.dump')
    def test_save_processed_intel(self, mock_json_dump, mock_open, analyst):
        """Test saving processed intelligence"""
        test_data = [{'title': 'Test', 'sentiment': 0.5, 'entities': []}]
        
        analyst.save_processed_intel(test_data)
        
        mock_open.assert_called_once_with('processed_intel.json', 'w')
        mock_json_dump.assert_called_once()
    
    @patch('analyst.glob.glob')
    @patch('builtins.open', create=True)
    @patch('analyst.json.load')
    def test_load_latest_intel(self, mock_json_load, mock_open, mock_glob, analyst):
        """Test loading the latest intelligence file"""
        mock_glob.return_value = ['intel_data/file1.json', 'intel_data/file2.json']
        mock_json_load.return_value = [{'title': 'Test'}]
        
        with patch('analyst.os.path.getctime', side_effect=[100, 200]):
            result = analyst.load_latest_intel()
        
        assert result == [{'title': 'Test'}]
    
    @patch('analyst.glob.glob')
    def test_load_latest_intel_handles_no_files(self, mock_glob, analyst):
        """Test handling when no intelligence files exist"""
        mock_glob.return_value = []
        
        result = analyst.load_latest_intel()
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
