"""MongoDB handler for article storage and retrieval."""
import logging
from typing import Optional, List, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from .config import MONGODB_URI, MONGODB_DB_NAME, MONGODB_COLLECTION_NAME

logger = logging.getLogger(__name__)


class MongoHandler:
    """Handle all MongoDB operations for article storage."""
    
    def __init__(self):
        """Initialize MongoDB handler with configuration."""
        self.uri = MONGODB_URI
        self.db_name = MONGODB_DB_NAME
        self.collection_name = MONGODB_COLLECTION_NAME
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        logger.info(f"Initialized MongoHandler for database: {self.db_name}, collection: {self.collection_name}")
    
    def connect(self):
        """Establish connection to MongoDB and test it.
        
        Raises:
            ConnectionFailure: If connection to MongoDB fails.
        """
        try:
            self.client = MongoClient(self.uri)
            # Test connection with ping
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            logger.info(f"Successfully connected to MongoDB: {self.db_name}.{self.collection_name}")
        except ConnectionFailure as e:
            error_msg = (
                f"Failed to connect to MongoDB. Please check:\n"
                f"1. MongoDB URI is correct: {self.uri[:20]}...\n"
                f"2. IP address is whitelisted in MongoDB Atlas\n"
                f"3. Network connectivity is available\n"
                f"Error: {str(e)}"
            )
            logger.error(error_msg)
            raise
    
    def article_exists(self, article_id: str) -> bool:
        """Check if an article with the given article_id already exists.
        
        Args:
            article_id: Unique identifier for the article (MD5 hash of URL)
            
        Returns:
            True if article exists, False otherwise
        """
        try:
            result = self.collection.find_one({"article_id": article_id})
            exists = result is not None
            if exists:
                logger.debug(f"Article already exists: {article_id}")
            return exists
        except PyMongoError as e:
            logger.error(f"Error checking if article exists: {str(e)}")
            return False
    
    def insert_article(self, article_dict: Dict) -> bool:
        """Insert an article into MongoDB if it doesn't already exist.
        
        Args:
            article_dict: Dictionary containing article data matching MongoDB schema
            
        Returns:
            True if article was inserted, False if it already exists or error occurred
        """
        article_id = article_dict.get("article_id")
        
        if not article_id:
            logger.error("Article dictionary missing 'article_id' field")
            return False
        
        # Check if article already exists
        if self.article_exists(article_id):
            logger.info(f"Article already exists, skipping: {article_id}")
            return False
        
        try:
            self.collection.insert_one(article_dict)
            logger.debug(f"Successfully inserted article: {article_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Error inserting article {article_id}: {str(e)}")
            return False
    
    def get_article_count(self) -> int:
        """Get total number of articles in the collection.
        
        Returns:
            Total count of articles
        """
        try:
            count = self.collection.count_documents({})
            logger.debug(f"Total articles in collection: {count}")
            return count
        except PyMongoError as e:
            logger.error(f"Error getting article count: {str(e)}")
            return 0
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch all articles from MongoDB.
        
        Args:
            limit: Optional limit on number of articles to fetch
            
        Returns:
            List of article dictionaries
        """
        try:
            if limit:
                articles = list(self.collection.find().limit(limit))
            else:
                articles = list(self.collection.find())
            logger.debug(f"Fetched {len(articles)} articles from MongoDB")
            return articles
        except PyMongoError as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

