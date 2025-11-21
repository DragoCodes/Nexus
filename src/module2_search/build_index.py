"""Script to build and save the inverted index from MongoDB."""

import sys
from pathlib import Path

# Add parent directory to path to import from module1
sys.path.insert(0, str(Path(__file__).parent.parent))

from module1_ingestion.local_db_handler import LocalDBHandler
from module1_ingestion.config import validate_config, DB_PATH
from .preprocessor import TextPreprocessor
from .indexer import InvertedIndex
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Build inverted index from MongoDB and save to disk."""
    print("=" * 60)
    print("Starting index build...")
    print("=" * 60)
    
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        
        # Connect to local database
        logger.info("Connecting to local database...")
        db_handler = LocalDBHandler(db_path=DB_PATH)
        db_handler.connect()
        
        # Check if there are articles
        article_count = db_handler.get_article_count()
        if article_count == 0:
            print("ERROR: No articles found in database!")
            print("Please run Module 1 ingestion first to populate the database.")
            db_handler.close()
            return
        
        print(f"Found {article_count} articles in database")
        
        # Create preprocessor
        logger.info("Initializing text preprocessor...")
        preprocessor = TextPreprocessor()
        
        # Create inverted index
        logger.info("Creating inverted index...")
        index = InvertedIndex(preprocessor)
        
        # Build index from database
        logger.info("Building index from database articles...")
        index.build_from_db(db_handler)
        
        # Save index to disk
        index_path = Path(__file__).parent.parent.parent / "data" / "index" / "inverted_index.pkl"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving index to {index_path}...")
        index.save_to_disk(str(index_path))
        
        # Print final statistics
        print("\n" + "=" * 60)
        print("Index build complete!")
        print("=" * 60)
        print(f"Index saved to: {index_path}")
        print(f"Total documents indexed: {index.num_docs}")
        print(f"Unique terms: {len(index.index)}")
        print(f"Average document length: {index.avg_doc_length:.2f} tokens")
        print("=" * 60)
        
        # Close connections
        db_handler.close()
        logger.info("Database connection closed")
        
    except Exception as e:
        logger.error(f"Error during index build: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        print("Please check the error message above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()

