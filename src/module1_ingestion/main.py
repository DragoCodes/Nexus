"""Main script to run article ingestion."""
import logging
import sys

from .config import validate_config, NEWS_API_KEY, DB_PATH
from .news_api_client import NewsAPIClient
from .local_db_handler import LocalDBHandler
from .ingestion_service import IngestionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Financial search queries
FINANCIAL_QUERIES = [
    "merger acquisition",
    "stock market",
    "IPO",
    "earnings report",
    "CEO resignation",
    "partnership deal",
    "investment funding",
    "bankruptcy",
    "regulatory approval",
    "market trends"
]


def main():
    """Main function to run article ingestion."""
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        logger.info("Configuration validated successfully")
        
        # Initialize clients and handlers
        logger.info("Initializing clients and handlers...")
        news_client = NewsAPIClient(api_key=NEWS_API_KEY)
        db_handler = LocalDBHandler(db_path=DB_PATH)
        
        # Connect to local database
        logger.info("Connecting to local database...")
        db_handler.connect()
        
        # Get initial article count
        initial_count = db_handler.get_article_count()
        logger.info(f"Initial article count in database: {initial_count}")
        
        # Create ingestion service
        ingestion_service = IngestionService(
            news_client=news_client,
            db_handler=db_handler
        )
        
        # Run ingestion for all queries
        # Start with max 100 articles per query for testing
        logger.info("Starting article ingestion...")
        aggregate_stats = ingestion_service.ingest_multiple_queries(
            query_list=FINANCIAL_QUERIES,
            max_articles_per_query=100  # Start with 100 for testing
        )
        
        # Print detailed statistics
        print("\n" + "="*80)
        print("INGESTION COMPLETE - DETAILED STATISTICS")
        print("="*80)
        print(f"\nTotal Queries Processed: {aggregate_stats['total_queries']}")
        print(f"Total Articles Fetched: {aggregate_stats['total_fetched']}")
        print(f"Total Articles Inserted: {aggregate_stats['total_inserted']}")
        print(f"Total Duplicates Skipped: {aggregate_stats['total_duplicates']}")
        print(f"Total Errors: {aggregate_stats['total_errors']}")
        
        print("\n" + "-"*80)
        print("Per-Query Statistics:")
        print("-"*80)
        for query_stat in aggregate_stats['query_stats']:
            print(f"\nQuery: '{query_stat['query']}'")
            print(f"  Fetched: {query_stat['fetched']}")
            print(f"  Inserted: {query_stat['inserted']}")
            print(f"  Duplicates: {query_stat['duplicates']}")
            print(f"  Errors: {query_stat['errors']}")
        
        # Get final article count
        final_count = db_handler.get_article_count()
        logger.info(f"Final article count in database: {final_count}")
        print(f"\n{'='*80}")
        print(f"Final Article Count in Database: {final_count}")
        print(f"{'='*80}\n")
        
        # Close connections
        logger.info("Closing connections...")
        db_handler.close()
        logger.info("Ingestion process completed successfully")
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

