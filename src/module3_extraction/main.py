"""Main script to run extraction on article corpus."""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
import os

from src.module1_ingestion.local_db_handler import LocalDBHandler
from src.module1_ingestion.config import DB_PATH
from src.module3_extraction.llm_client import GeminiClient
from src.module3_extraction.prompt_manager import PromptManager
from src.module3_extraction.output_parser import ExtractionParser
from src.module3_extraction.cache import ExtractionCache
from src.module3_extraction.extraction_service import ExtractionService
from src.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(__name__)


def load_config():
    """Load configuration from environment variables."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    return {
        "gemini_api_key": gemini_api_key,
        "db_path": DB_PATH
    }


def fetch_articles_from_db(
    db_handler: LocalDBHandler,
    limit: int = None,
    skip: int = 0
) -> List[Dict]:
    """Fetch articles from database.
    
    Args:
        db_handler: Database handler instance
        limit: Maximum number of articles to fetch
        skip: Number of articles to skip
        
    Returns:
        List of article dictionaries
    """
    try:
        db_handler.connect()
        
        query = {}
        cursor = db_handler.collection.find(query).skip(skip)
        
        if limit:
            cursor = cursor.limit(limit)
        
        articles = list(cursor)
        
        # Normalize article structure to match expected format
        normalized_articles = []
        for article in articles:
            normalized = {
                "article_id": article.get("article_id", ""),
                "headline": article.get("headline", ""),
                "text": article.get("full_text", ""),
                "published_at": article.get("publication_date", "")
            }
            normalized_articles.append(normalized)
        
        logger.info(f"Fetched {len(normalized_articles)} articles from database")
        return normalized_articles
        
    except Exception as e:
        logger.error(f"Error fetching articles from database: {str(e)}")
        raise
    finally:
        db_handler.close()


def save_results(results: List[Dict], output_file: str):
    """Save extraction results to JSON file.
    
    Args:
        results: List of extraction results
        output_file: Path to output JSON file
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(results)} extraction results to {output_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        raise


def save_intermediate_results(results: List[Dict], output_file: str, batch_num: int):
    """Save intermediate results during batch processing.
    
    Args:
        results: List of extraction results so far
        output_file: Base path for output file
        batch_num: Current batch number
    """
    intermediate_file = Path(output_file).with_suffix(f'.batch_{batch_num}.json')
    save_results(results, str(intermediate_file))
    logger.info(f"Saved intermediate results to {intermediate_file}")


def main():
    """Main extraction script."""
    parser = argparse.ArgumentParser(
        description="Extract financial relationships from news articles"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to process"
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Number of articles to skip (for resuming)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of articles per batch"
    )
    parser.add_argument(
        "--delay-between-batches",
        type=int,
        default=30,
        help="Seconds to wait between batches"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-extraction (ignore cache)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/exports/extractions.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default="data/cache/extraction_cache.json",
        help="Cache file path"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Starting Module 3: Information Extraction")
    logger.info("=" * 80)
    logger.info(f"Arguments: limit={args.limit}, skip={args.skip}, "
                f"batch_size={args.batch_size}, force={args.force}")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize database handler
        db_handler = LocalDBHandler(db_path=config["db_path"])
        db_handler.connect()
        
        # Fetch articles
        logger.info("Fetching articles from database...")
        articles = fetch_articles_from_db(
            db_handler=db_handler,
            limit=args.limit,
            skip=args.skip
        )
        
        if not articles:
            logger.warning("No articles found in database")
            return
        
        logger.info(f"Found {len(articles)} articles to process")
        
        # Initialize components
        logger.info("Initializing extraction components...")
        
        llm_client = GeminiClient(api_key=config["gemini_api_key"])
        prompt_manager = PromptManager()
        parser = ExtractionParser(
            allowed_relationship_types=prompt_manager.get_relationship_types(),
            allowed_entity_types=prompt_manager.get_entity_types()
        )
        cache = ExtractionCache(cache_file_path=args.cache_file)
        extraction_service = ExtractionService(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            parser=parser,
            cache=cache
        )
        
        # Run batch extraction
        logger.info("Starting batch extraction...")
        results = extraction_service.batch_extract(
            articles=articles,
            batch_size=args.batch_size,
            delay_between_batches=args.delay_between_batches,
            force_re_extract=args.force
        )
        
        # Save results
        logger.info("Saving extraction results...")
        save_results(results, args.output)
        
        # Print statistics
        stats = extraction_service.get_statistics()
        parser_stats = parser.get_statistics()
        
        logger.info("=" * 80)
        logger.info("EXTRACTION STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total articles processed: {stats['total_articles_processed']}")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        logger.info(f"API calls made: {stats['api_calls_made']}")
        logger.info(f"Successful extractions: {stats['successful_extractions']}")
        logger.info(f"Failed extractions: {stats['failed_extractions']}")
        logger.info(f"Total relationships extracted: {stats['total_relationships_extracted']}")
        logger.info(
            f"Average relationships per article: "
            f"{stats['average_relationships_per_article']:.2f}"
        )
        logger.info(f"Parser - Total received: {parser_stats['total_received']}")
        logger.info(f"Parser - Valid: {parser_stats['valid']}")
        logger.info(f"Parser - Invalid: {parser_stats['invalid']}")
        
        # Estimate cost (rough estimate based on API calls)
        # Note: This is a rough estimate. Actual cost depends on token usage.
        logger.info("=" * 80)
        logger.info("COST ESTIMATION")
        logger.info("=" * 80)
        logger.info(
            f"API calls made: {stats['api_calls_made']} "
            f"(Note: Actual cost depends on token usage per call)"
        )
        logger.info(
            "For accurate cost estimation, monitor token usage in Gemini API dashboard"
        )
        
        logger.info("=" * 80)
        logger.info("Extraction completed successfully!")
        logger.info(f"Results saved to: {args.output}")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.warning("Extraction interrupted by user")
        logger.info("Saving intermediate results...")
        # Save whatever we have so far
        if 'results' in locals():
            intermediate_file = Path(args.output).with_suffix('.interrupted.json')
            save_results(results, str(intermediate_file))
            logger.info(f"Intermediate results saved to {intermediate_file}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

