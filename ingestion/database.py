"""
Database Manager for Article Storage
Handles SQLite operations with thread-safety and duplicate detection
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid
from contextlib import contextmanager


class ArticleDatabase:
    def __init__(self, db_path: str = "data/articles.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize_db()
    
    def _initialize_db(self):
        """Create tables if they don't exist"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    article_id TEXT PRIMARY KEY,
                    headline TEXT NOT NULL,
                    full_text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    processed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    url TEXT,
                    UNIQUE(headline, source, publication_date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_publication_date 
                ON articles(publication_date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed 
                ON articles(processed)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_article(self, article: Dict) -> Optional[str]:
        """
        Insert a new article with duplicate detection
        Returns article_id if successful, None if duplicate
        """
        article_id = article.get('article_id', str(uuid.uuid4()))
        
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO articles 
                    (article_id, headline, full_text, source, publication_date, url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article_id,
                    article['headline'],
                    article['full_text'],
                    article['source'],
                    article['publication_date'],
                    article.get('url', '')
                ))
                conn.commit()
                return article_id
            except sqlite3.IntegrityError:
                # Duplicate article
                return None
    
    def bulk_insert(self, articles: List[Dict]) -> Dict[str, int]:
        """Bulk insert with statistics"""
        stats = {'inserted': 0, 'duplicates': 0, 'errors': 0}
        
        for article in articles:
            try:
                result = self.insert_article(article)
                if result:
                    stats['inserted'] += 1
                else:
                    stats['duplicates'] += 1
            except Exception as e:
                stats['errors'] += 1
                print(f"Error inserting article: {e}")
        
        return stats
    
    def get_article(self, article_id: str) -> Optional[Dict]:
        """Retrieve a single article by ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM articles WHERE article_id = ?",
                (article_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all articles, optionally limited"""
        with self._get_connection() as conn:
            query = "SELECT * FROM articles ORDER BY publication_date DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unprocessed_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Get articles that haven't been processed for extraction"""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM articles 
                WHERE processed = 0 
                ORDER BY publication_date DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_processed(self, article_id: str):
        """Mark an article as processed"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE articles SET processed = 1 WHERE article_id = ?",
                (article_id,)
            )
            conn.commit()
    
    def export_to_json(self, output_path: str = "data/articles_export.json"):
        """Export all articles to JSON file"""
        articles = self.get_all_articles()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        return len(articles)
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed,
                    COUNT(DISTINCT source) as sources,
                    MIN(publication_date) as earliest_date,
                    MAX(publication_date) as latest_date
                FROM articles
            """)
            row = cursor.fetchone()
            return dict(row)


# Quick test
if __name__ == "__main__":
    db = ArticleDatabase()
    
    # Test article
    test_article = {
        "headline": "Test Article",
        "full_text": "This is a test article about NVIDIA and AI.",
        "source": "Test Source",
        "publication_date": datetime.now().isoformat(),
        "url": "https://example.com/test"
    }
    
    article_id = db.insert_article(test_article)
    print(f"Inserted article: {article_id}")
    
    stats = db.get_statistics()
    print(f"Database stats: {stats}")