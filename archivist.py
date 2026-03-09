import sqlite3
import json
import os

class IntelArchivist:
    def __init__(self, db_name="intel_graph.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to the SQLite Database"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        print(f"[*] Connected to database: {self.db_name}")

    def create_schema(self):
        """
        Defines the structure of our database (The Schema).
        We use a Relational Model: Articles <--- one-to-many ---> Entities
        """
        # 1. Table for the Articles
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                source TEXT,
                published_at TEXT,
                sentiment REAL,
                summary TEXT,
                region TEXT
            )
        ''')

        # 2. Table for the Entities (People, Orgs, Locations)
        # The 'article_id' links this entity back to the specific news story
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                name TEXT,
                type TEXT,
                FOREIGN KEY(article_id) REFERENCES articles(id)
            )
        ''')
        self.conn.commit()
        print("[+] Database schema verified.")

    def ingest_data(self, json_file, region="Unknown"):
        """
        Reads the processed JSON and inserts it into the SQL database.
        """
        if not os.path.exists(json_file):
            print(f"[!] File not found: {json_file}")
            return

        with open(json_file, 'r') as f:
            data = json.load(f)

        count_new = 0
        print(f"[*] Archiving {len(data)} items into SQL...")

        for item in data:
            try:
                # 1. Insert Article
                # We use INSERT OR IGNORE to prevent duplicates if you run this twice
                self.cursor.execute('''
                    INSERT OR IGNORE INTO articles (title, source, published_at, sentiment, region)
                    VALUES (?, ?, ?, ?, ?)
                ''', (item['title'], item['source'], item['published_at'], item['sentiment'], region))
                
                # If the article was skipped (duplicate), don't add entities
                if self.cursor.rowcount == 0:
                    continue
                
                # Get the ID of the article we just created
                article_id = self.cursor.lastrowid
                count_new += 1

                # 2. Insert Entities linked to that Article
                for ent_name, ent_type in item['entities']:
                    self.cursor.execute('''
                        INSERT INTO entities (article_id, name, type)
                        VALUES (?, ?, ?)
                    ''', (article_id, ent_name, ent_type))

            except sqlite3.Error as e:
                print(f"[!] Database Error: {e}")

        self.conn.commit()
        print(f"[+] Archival complete. Added {count_new} new intelligence reports.")

    def close(self):
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    # 1. Initialize Archivist
    archivist = IntelArchivist()
    
    # 2. Connect & Setup
    archivist.connect()
    archivist.create_schema()
    
    # 3. Ingest Data
    # Takes the output from Phase 2
    archivist.ingest_data("processed_intel.json")
    
    # 4. Cleanup
    archivist.close()