"""Cache for extraction results to avoid redundant API calls."""
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractionCache:
    """Cache extraction results to disk."""
    
    def __init__(self, cache_file_path: str):
        """Initialize cache.
        
        Args:
            cache_file_path: Path to cache JSON file (e.g., data/cache/extraction_cache.json)
        """
        self.cache_file_path = Path(cache_file_path)
        self.cache: Dict = {}
        self.load()
        logger.info(f"Initialized ExtractionCache with {len(self.cache)} cached entries")
    
    def get(self, article_id: str) -> Optional[List[Dict]]:
        """Get cached extractions for an article.
        
        Args:
            article_id: Article identifier
            
        Returns:
            List of relationships if cached, None otherwise
        """
        if article_id in self.cache:
            logger.debug(f"Cache hit for article: {article_id}")
            return self.cache[article_id].get("relationships", [])
        
        logger.debug(f"Cache miss for article: {article_id}")
        return None
    
    def set(self, article_id: str, extractions: List[Dict]):
        """Store extractions in cache.
        
        Args:
            article_id: Article identifier
            extractions: List of extracted relationships
        """
        self.cache[article_id] = {
            "extracted_at": datetime.now().isoformat(),
            "relationships": extractions,
            "relationship_count": len(extractions)
        }
        
        logger.debug(
            f"Cached {len(extractions)} relationships for article: {article_id}"
        )
        
        # Auto-save after every update
        self.save()
    
    def exists(self, article_id: str) -> bool:
        """Check if article is cached.
        
        Args:
            article_id: Article identifier
            
        Returns:
            True if cached, False otherwise
        """
        return article_id in self.cache
    
    def save(self):
        """Save cache to disk."""
        try:
            # Create parent directory if it doesn't exist
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file with pretty printing
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved cache to {self.cache_file_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def load(self):
        """Load cache from disk."""
        if not self.cache_file_path.exists():
            logger.info(f"Cache file not found, starting with empty cache: {self.cache_file_path}")
            self.cache = {}
            return
        
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
            
            logger.info(f"Loaded cache with {len(self.cache)} entries from {self.cache_file_path}")
        except json.JSONDecodeError as e:
            # Backup corrupted file
            backup_path = self.cache_file_path.with_suffix('.json.backup')
            logger.warning(
                f"Cache file corrupted. Backing up to {backup_path} and starting fresh."
            )
            try:
                self.cache_file_path.rename(backup_path)
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted cache: {backup_error}")
            
            self.cache = {}
        except Exception as e:
            logger.error(f"Failed to load cache: {str(e)}")
            self.cache = {}
    
    def get_cache_size(self) -> int:
        """Get number of cached articles."""
        return len(self.cache)
    
    def clear(self):
        """Clear all cache entries (use with caution)."""
        self.cache = {}
        self.save()
        logger.warning("Cache cleared")

