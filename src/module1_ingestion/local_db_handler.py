"""Local SQLite database handler for article storage and retrieval."""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalDBHandler:
    """Handle all database operations for article storage using SQLite."""
    
    def __init__(self, db_path: str = "data/articles.db"):
        """Initialize local database handler.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized LocalDBHandler with database: {db_path}")
        self._create_tables()
    
    def _create_tables(self):
        """Create articles table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                article_id TEXT PRIMARY KEY,
                publication_date TEXT NOT NULL,
                source TEXT NOT NULL,
                headline TEXT NOT NULL,
                full_text TEXT NOT NULL,
                url TEXT NOT NULL,
                author TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_publication_date 
            ON articles(publication_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source 
            ON articles(source)
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database tables created/verified")
    
    def connect(self):
        """Establish connection to SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Successfully connected to local database: {self.db_path}")
        except sqlite3.Error as e:
            error_msg = f"Failed to connect to local database: {str(e)}"
            logger.error(error_msg)
            raise
    
    def article_exists(self, article_id: str) -> bool:
        """Check if an article with the given article_id already exists.
        
        Args:
            article_id: Unique identifier for the article (MD5 hash of URL)
            
        Returns:
            True if article exists, False otherwise
        """
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT article_id FROM articles WHERE article_id = ?", (article_id,))
            result = cursor.fetchone()
            exists = result is not None
            if exists:
                logger.debug(f"Article already exists: {article_id}")
            return exists
        except sqlite3.Error as e:
            logger.error(f"Error checking if article exists: {str(e)}")
            return False
    
    def insert_article(self, article_dict: Dict) -> bool:
        """Insert an article into the database if it doesn't already exist.
        
        Args:
            article_dict: Dictionary containing article data
            
        Returns:
            True if article was inserted, False if it already exists or error occurred
        """
        if not self.conn:
            self.connect()
        
        article_id = article_dict.get("article_id")
        
        if not article_id:
            logger.error("Article dictionary missing 'article_id' field")
            return False
        
        # Check if article already exists
        if self.article_exists(article_id):
            logger.info(f"Article already exists, skipping: {article_id}")
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO articles (
                    article_id, publication_date, source, headline,
                    full_text, url, author, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article_dict.get("article_id"),
                article_dict.get("publication_date"),
                article_dict.get("source"),
                article_dict.get("headline"),
                article_dict.get("full_text", ""),
                article_dict.get("url"),
                article_dict.get("author"),
                article_dict.get("created_at")
            ))
            self.conn.commit()
            logger.debug(f"Successfully inserted article: {article_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting article {article_id}: {str(e)}")
            return False
    
    def get_article_count(self) -> int:
        """Get total number of articles in the database.
        
        Returns:
            Total count of articles
        """
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM articles")
            result = cursor.fetchone()
            count = result['count'] if result else 0
            logger.debug(f"Total articles in database: {count}")
            return count
        except sqlite3.Error as e:
            logger.error(f"Error getting article count: {str(e)}")
            return 0
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch all articles from the database.
        
        Args:
            limit: Optional limit on number of articles to fetch
            
        Returns:
            List of article dictionaries
        """
        if not self.conn:
            self.connect()
        
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute("SELECT * FROM articles LIMIT ?", (limit,))
            else:
                cursor.execute("SELECT * FROM articles")
            
            rows = cursor.fetchall()
            articles = []
            for row in rows:
                articles.append({
                    'article_id': row['article_id'],
                    'publication_date': row['publication_date'],
                    'source': row['source'],
                    'headline': row['headline'],
                    'full_text': row['full_text'],
                    'url': row['url'],
                    'author': row['author'],
                    'created_at': row['created_at']
                })
            
            logger.debug(f"Fetched {len(articles)} articles from database")
            return articles
        except sqlite3.Error as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []
    
    def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict]:
        """Fetch articles by their IDs.
        
        Args:
            article_ids: List of article IDs to fetch
            
        Returns:
            List of article dictionaries
        """
        if not self.conn:
            self.connect()
        
        if not article_ids:
            return []
        
        try:
            cursor = self.conn.cursor()
            # Create placeholders for IN clause
            placeholders = ','.join(['?'] * len(article_ids))
            cursor.execute(f"SELECT * FROM articles WHERE article_id IN ({placeholders})", article_ids)
            
            rows = cursor.fetchall()
            articles = []
            for row in rows:
                articles.append({
                    'article_id': row['article_id'],
                    'publication_date': row['publication_date'],
                    'source': row['source'],
                    'headline': row['headline'],
                    'full_text': row['full_text'],
                    'url': row['url'],
                    'author': row['author'],
                    'created_at': row['created_at']
                })
            
            return articles
        except sqlite3.Error as e:
            logger.error(f"Error fetching articles by IDs: {str(e)}")
            return []
    
    @property
    def collection(self):
        """Compatibility property for MongoDB-style access."""
        # Return a mock object that supports find() method
        return self
    
    def find(self, query: Optional[Dict] = None):
        """MongoDB-style find() method for compatibility.
        
        Args:
            query: Dictionary with query conditions (currently supports article_id only)
            
        Returns:
            Mock cursor-like object
        """
        if not self.conn:
            self.connect()
        
        class MockCursor:
            def __init__(self, articles):
                self.articles = articles
                self._skip = 0
                self._limit = None
            
            def skip(self, n):
                """Skip n articles (MongoDB-style)."""
                self._skip = n
                return self
            
            def limit(self, n):
                """Limit to n articles (MongoDB-style)."""
                self._limit = n
                return self
            
            def __iter__(self):
                # Apply skip and limit
                result = self.articles[self._skip:]
                if self._limit is not None:
                    result = result[:self._limit]
                return iter(result)
            
            def __next__(self):
                return next(iter(self))
        
        if query and 'article_id' in query:
            article_ids = query['article_id']
            if isinstance(article_ids, dict) and '$in' in article_ids:
                # Handle MongoDB-style $in query
                ids_list = article_ids['$in']
                articles = self.get_articles_by_ids(ids_list)
                return MockCursor(articles)
        
        # Default: return all articles
        articles = self.get_all_articles()
        return MockCursor(articles)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

