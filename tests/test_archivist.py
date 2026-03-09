"""
Unit tests for the IntelArchivist module.
"""
import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from archivist import IntelArchivist


class TestIntelArchivist:
    """Test suite for IntelArchivist class"""
    
    @pytest.fixture
    def archivist(self):
        """Create an archivist instance for testing"""
        return IntelArchivist(":memory:")  # Use in-memory database for testing
    
    @pytest.fixture
    def connected_archivist(self, archivist):
        """Create and connect an archivist instance"""
        archivist.connect()
        archivist.create_schema()
        yield archivist
        archivist.close()
    
    def test_initialization(self):
        """Test that archivist initializes correctly"""
        archivist = IntelArchivist("test.db")
        assert archivist.db_name == "test.db"
        assert archivist.conn is None
        assert archivist.cursor is None
    
    def test_connect_establishes_connection(self, archivist):
        """Test database connection"""
        archivist.connect()
        
        assert archivist.conn is not None
        assert archivist.cursor is not None
        
        archivist.close()
    
    def test_create_schema_creates_tables(self, archivist):
        """Test that schema creation works"""
        archivist.connect()
        archivist.create_schema()
        
        # Check that tables exist
        archivist.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in archivist.cursor.fetchall()]
        
        assert 'articles' in tables
        assert 'entities' in tables
        
        archivist.close()
    
    def test_articles_table_has_correct_schema(self, connected_archivist):
        """Test articles table structure"""
        connected_archivist.cursor.execute("PRAGMA table_info(articles)")
        columns = {row[1] for row in connected_archivist.cursor.fetchall()}
        
        expected_columns = {'id', 'title', 'source', 'published_at', 
                          'sentiment', 'summary', 'region'}
        assert expected_columns.issubset(columns)
    
    def test_entities_table_has_foreign_key(self, connected_archivist):
        """Test entities table has foreign key relationship"""
        connected_archivist.cursor.execute("PRAGMA foreign_key_list(entities)")
        foreign_keys = connected_archivist.cursor.fetchall()
        
        assert len(foreign_keys) > 0
        assert foreign_keys[0][2] == 'articles'  # References articles table
    
    @patch('builtins.open', create=True)
    @patch('archivist.json.load')
    def test_ingest_data_inserts_articles(self, mock_json_load, mock_open, 
                                         connected_archivist):
        """Test inserting articles into database"""
        test_data = [
            {
                'title': 'Test Article',
                'source': 'Test Source',
                'published_at': '2026-03-09',
                'sentiment': 0.5,
                'entities': [('Iran', 'GPE'), ('UN', 'ORG')]
            }
        ]
        mock_json_load.return_value = test_data
        
        with patch('archivist.os.path.exists', return_value=True):
            connected_archivist.ingest_data('test.json', region='Test Region')
        
        # Verify article was inserted
        connected_archivist.cursor.execute("SELECT COUNT(*) FROM articles")
        count = connected_archivist.cursor.fetchone()[0]
        assert count == 1
        
        # Verify entities were inserted
        connected_archivist.cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = connected_archivist.cursor.fetchone()[0]
        assert entity_count == 2
    
    @patch('builtins.open', create=True)
    @patch('archivist.json.load')
    def test_ingest_data_prevents_duplicates(self, mock_json_load, mock_open,
                                            connected_archivist):
        """Test that duplicate articles are not inserted"""
        test_data = [
            {
                'title': 'Duplicate Article',
                'source': 'Test',
                'published_at': '2026-03-09',
                'sentiment': 0.0,
                'entities': []
            }
        ]
        mock_json_load.return_value = test_data
        
        with patch('archivist.os.path.exists', return_value=True):
            # Insert once
            connected_archivist.ingest_data('test.json', region='Test')
            
            # Try to insert again
            connected_archivist.ingest_data('test.json', region='Test')
        
        # Should only have 1 article
        connected_archivist.cursor.execute("SELECT COUNT(*) FROM articles")
        count = connected_archivist.cursor.fetchone()[0]
        assert count == 1
    
    def test_ingest_data_handles_missing_file(self, connected_archivist, capsys):
        """Test handling of missing JSON file"""
        with patch('archivist.os.path.exists', return_value=False):
            connected_archivist.ingest_data('nonexistent.json')
        
        captured = capsys.readouterr()
        assert "[!] File not found" in captured.out
    
    @patch('builtins.open', create=True)
    @patch('archivist.json.load')
    def test_ingest_data_stores_region(self, mock_json_load, mock_open,
                                      connected_archivist):
        """Test that region is stored correctly"""
        test_data = [
            {
                'title': 'Regional Article',
                'source': 'Test',
                'published_at': '2026-03-09',
                'sentiment': 0.0,
                'entities': []
            }
        ]
        mock_json_load.return_value = test_data
        
        with patch('archivist.os.path.exists', return_value=True):
            connected_archivist.ingest_data('test.json', region='Middle East')
        
        # Check region was stored
        connected_archivist.cursor.execute(
            "SELECT region FROM articles WHERE title = 'Regional Article'"
        )
        region = connected_archivist.cursor.fetchone()[0]
        assert region == 'Middle East'
    
    def test_close_closes_connection(self, archivist):
        """Test that close properly closes the connection"""
        archivist.connect()
        conn = archivist.conn
        archivist.close()
        
        # Try to execute a query on the closed connection
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
    
    @patch('builtins.open', create=True)
    @patch('archivist.json.load')
    def test_ingest_data_handles_database_error(self, mock_json_load, mock_open,
                                               connected_archivist, capsys):
        """Test handling of database errors"""
        # Create malformed data that will cause an error
        test_data = [
            {
                'title': 'Test',
                'source': 'Test',
                'published_at': '2026-03-09',
                'sentiment': 'invalid',  # Should be a number
                'entities': []
            }
        ]
        mock_json_load.return_value = test_data
        
        with patch('archivist.os.path.exists', return_value=True):
            connected_archivist.ingest_data('test.json')
        
        captured = capsys.readouterr()
        assert "[!] Database Error" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
