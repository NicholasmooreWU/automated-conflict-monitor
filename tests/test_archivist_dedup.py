import pytest
import sqlite3
import os
import json
from archivist import IntelArchivist

def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    archivist = IntelArchivist(str(db_path))
    archivist.connect()
    archivist.create_schema()
    return archivist, db_path

def test_ingest_data_dedup(tmp_path):
    archivist, db_path = setup_db(tmp_path)
    test_data = [
        {'title': 'Unique Article', 'source': 'Test', 'published_at': '2026-04-01', 'sentiment': 0.1, 'entities': [('A', 'GPE')]},
        {'title': 'Unique Article', 'source': 'Test', 'published_at': '2026-04-01', 'sentiment': 0.1, 'entities': [('A', 'GPE')]},
    ]
    json_path = tmp_path / "test.json"
    with open(json_path, 'w') as f:
        json.dump(test_data, f)
    archivist.ingest_data(str(json_path), region="Test")
    # Only one article should be inserted
    archivist.cursor.execute("SELECT COUNT(*) FROM articles")
    count = archivist.cursor.fetchone()[0]
    assert count == 1
    archivist.close()
    os.remove(json_path)
    os.remove(db_path)
