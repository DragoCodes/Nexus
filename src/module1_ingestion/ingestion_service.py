"""Service to orchestrate the article ingestion process."""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .news_api_client import NewsAPIClient
from .local_db_handler import LocalDBHandler

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrate the ingestion of articles from News API to local database."""
    
    def __init__(self, news_client: NewsAPIClient, db_handler: LocalDBHandler):
        """Initialize ingestion service.
        
        Args:
            news_client: Instance of NewsAPIClient
            db_handler: Instance of LocalDBHandler
        """
        self.news_client = news_client
        self.db_handler = db_handler
        logger.info("Initialized IngestionService")
    
    def _transform_article(self, raw_article: Dict) -> Dict:
        """Transform News API article format to database schema.
        
        Args:
            raw_article: Article dictionary from News API
            
        Returns:
            Transformed article dictionary matching database schema
        """
        # Generate article_id from URL using MD5 hash
        url = raw_article.get("url", "")
        article_id = hashlib.md5(url.encode()).hexdigest()
        
        # Parse publication date
        publication_date = None
        published_at = raw_article.get("publishedAt")
        if published_at:
            try:
                # News API provides ISO format dates
                publication_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse publication date: {published_at}, error: {str(e)}")
        
        # Extract source name
        source = raw_article.get("source", {})
        source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)
        
        # Extract headline
        headline = raw_article.get("title", "")
        
        # Extract full text (prefer content, fallback to description)
        full_text = (
            raw_article.get("content") or
            raw_article.get("description") or
            ""
        )
        
        # Extract URL
        url = raw_article.get("url", "")
        
        # Extract author (can be None)
        author = raw_article.get("author")
        
        # Current timestamp for created_at
        created_at = datetime.utcnow()
        
        # Convert datetime to ISO string for SQLite storage
        publication_date_str = publication_date.isoformat() if publication_date else None
        created_at_str = created_at.isoformat()
        
        # Build database document
        article_dict = {
            "article_id": article_id,
            "publication_date": publication_date_str,
            "source": source_name,
            "headline": headline,
            "full_text": full_text,
            "url": url,
            "author": author,
            "created_at": created_at_str
        }
        
        return article_dict
    
    def ingest_articles_for_query(
        self,
        query: str,
        max_articles: int = 1000,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict:
        """Ingest articles for a given query.
        
        Args:
            query: Search query string
            max_articles: Maximum number of articles to fetch
            from_date: Start date in YYYY-MM-DD format (optional)
            to_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ingestion for query: '{query}'")
        
        stats = {
            "query": query,
            "fetched": 0,
            "inserted": 0,
            "duplicates": 0,
            "errors": 0
        }
        
        # Fetch articles from News API
        raw_articles = self.news_client.fetch_all_articles_for_query(
            query=query,
            max_articles=max_articles,
            from_date=from_date,
            to_date=to_date
        )
        
        stats["fetched"] = len(raw_articles)
        logger.info(f"Fetched {stats['fetched']} articles from API")
        
        # Process each article
        for idx, raw_article in enumerate(raw_articles, 1):
            try:
                # Transform article
                article_dict = self._transform_article(raw_article)
                
                # Try to insert
                if self.db_handler.insert_article(article_dict):
                    stats["inserted"] += 1
                else:
                    # Check if it was a duplicate or an error
                    if self.db_handler.article_exists(article_dict["article_id"]):
                        stats["duplicates"] += 1
                    else:
                        stats["errors"] += 1
                
                # Log progress every 10 articles
                if idx % 10 == 0:
                    logger.info(
                        f"Processed {idx}/{stats['fetched']} articles - "
                        f"Inserted: {stats['inserted']}, "
                        f"Duplicates: {stats['duplicates']}, "
                        f"Errors: {stats['errors']}"
                    )
                    
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error processing article {idx}: {str(e)}")
        
        logger.info(
            f"Completed ingestion for query '{query}': "
            f"Fetched: {stats['fetched']}, "
            f"Inserted: {stats['inserted']}, "
            f"Duplicates: {stats['duplicates']}, "
            f"Errors: {stats['errors']}"
        )
        
        return stats
    
    def ingest_multiple_queries(
        self,
        query_list: List[str],
        max_articles_per_query: int = 500
    ) -> Dict:
        """Ingest articles for multiple queries.
        
        Args:
            query_list: List of search query strings
            max_articles_per_query: Maximum articles to fetch per query
            
        Returns:
            Dictionary with aggregate statistics
        """
        logger.info(f"Starting ingestion for {len(query_list)} queries")
        
        aggregate_stats = {
            "total_queries": len(query_list),
            "total_fetched": 0,
            "total_inserted": 0,
            "total_duplicates": 0,
            "total_errors": 0,
            "query_stats": []
        }
        
        for idx, query in enumerate(query_list, 1):
            logger.info(f"Processing query {idx}/{len(query_list)}: '{query}'")
            
            # Ingest articles for this query
            stats = self.ingest_articles_for_query(
                query=query,
                max_articles=max_articles_per_query
            )
            
            # Update aggregate statistics
            aggregate_stats["total_fetched"] += stats["fetched"]
            aggregate_stats["total_inserted"] += stats["inserted"]
            aggregate_stats["total_duplicates"] += stats["duplicates"]
            aggregate_stats["total_errors"] += stats["errors"]
            aggregate_stats["query_stats"].append(stats)
            
            # Add delay between queries to respect rate limits (except for last query)
            if idx < len(query_list):
                delay = 5
                logger.info(f"Waiting {delay} seconds before next query...")
                import time
                time.sleep(delay)
        
        logger.info(
            f"Completed ingestion for all queries: "
            f"Total fetched: {aggregate_stats['total_fetched']}, "
            f"Total inserted: {aggregate_stats['total_inserted']}, "
            f"Total duplicates: {aggregate_stats['total_duplicates']}, "
            f"Total errors: {aggregate_stats['total_errors']}"
        )
        
        return aggregate_stats

