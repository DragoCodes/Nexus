"""Orchestrate the extraction process."""
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ExtractionService:
    """Orchestrate relationship extraction from articles."""
    
    def __init__(self, llm_client, prompt_manager, parser, cache):
        """Initialize extraction service.
        
        Args:
            llm_client: GeminiClient instance
            prompt_manager: PromptManager instance
            parser: ExtractionParser instance
            cache: ExtractionCache instance
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.parser = parser
        self.cache = cache
        
        # Statistics tracking
        self.stats = {
            "total_articles_processed": 0,
            "cache_hits": 0,
            "api_calls_made": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_relationships_extracted": 0
        }
        
        logger.info("Initialized ExtractionService")
    
    def extract_from_article(
        self,
        article_id: str,
        article_headline: str,
        article_text: str,
        force_re_extract: bool = False
    ) -> List[Dict]:
        """Extract relationships from a single article.
        
        Args:
            article_id: Unique article identifier
            article_headline: Article headline
            article_text: Full article text
            force_re_extract: If True, ignore cache and re-extract
            
        Returns:
            List of extracted relationships (empty list on failure)
        """
        self.stats["total_articles_processed"] += 1
        
        # Check cache first
        if not force_re_extract:
            cached_result = self.cache.get(article_id)
            if cached_result is not None:
                self.stats["cache_hits"] += 1
                self.stats["successful_extractions"] += 1
                self.stats["total_relationships_extracted"] += len(cached_result)
                return cached_result
        
        # Cache miss - need to extract
        try:
            # Generate prompt
            prompt = self.prompt_manager.generate_extraction_prompt(
                article_text=article_text,
                article_headline=article_headline
            )
            
            # Call LLM
            llm_response = self.llm_client.extract(prompt)
            
            if llm_response is None:
                logger.warning(f"LLM extraction failed for article: {article_id}")
                self.stats["failed_extractions"] += 1
                return []
            
            self.stats["api_calls_made"] += 1
            
            # Parse response
            relationships = self.parser.parse(llm_response)
            
            if relationships is None:
                logger.warning(f"Parsing failed for article: {article_id}")
                self.stats["failed_extractions"] += 1
                return []
            
            # Cache result
            self.cache.set(article_id, relationships)
            
            # Update statistics
            self.stats["successful_extractions"] += 1
            self.stats["total_relationships_extracted"] += len(relationships)
            
            logger.debug(
                f"Extracted {len(relationships)} relationships from article: {article_id}"
            )
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error extracting from article {article_id}: {str(e)}", exc_info=True)
            self.stats["failed_extractions"] += 1
            return []
    
    def batch_extract(
        self,
        articles: List[Dict],
        batch_size: int = 10,
        delay_between_batches: int = 30,
        delay_between_calls: float = 4.5,
        force_re_extract: bool = False
    ) -> List[Dict]:
        """Process articles in batches.
        
        Args:
            articles: List of article dictionaries with keys: article_id, headline, text
            batch_size: Number of articles per batch
            delay_between_batches: Seconds to wait between batches
            delay_between_calls: Seconds to wait between API calls within batch
            force_re_extract: If True, ignore cache
            
        Returns:
            List of all extracted relationships with article metadata
        """
        total_articles = len(articles)
        all_results = []
        
        logger.info(
            f"Starting batch extraction: {total_articles} articles, "
            f"batch_size={batch_size}, delay_between_batches={delay_between_batches}s"
        )
        
        for batch_start in range(0, total_articles, batch_size):
            batch_end = min(batch_start + batch_size, total_articles)
            batch_articles = articles[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_articles + batch_size - 1) // batch_size
            
            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"(articles {batch_start + 1}-{batch_end} of {total_articles})"
            )
            
            # Process articles in batch
            for idx, article in enumerate(batch_articles):
                article_id = article.get("article_id")
                headline = article.get("headline", article.get("title", ""))
                text = article.get("text", article.get("content", ""))
                
                if not article_id:
                    logger.warning(f"Skipping article without article_id: {article}")
                    continue
                
                if not text:
                    logger.warning(f"Skipping article without text: {article_id}")
                    continue
                
                # Extract relationships
                relationships = self.extract_from_article(
                    article_id=article_id,
                    article_headline=headline,
                    article_text=text,
                    force_re_extract=force_re_extract
                )
                
                # Store result with article metadata
                all_results.append({
                    "article_id": article_id,
                    "publication_date": article.get("published_at", article.get("publishedAt", "")),
                    "relationships": relationships
                })
                
                # Progress update
                processed = self.stats["total_articles_processed"]
                cache_hits = self.stats["cache_hits"]
                api_calls = self.stats["api_calls_made"]
                
                logger.info(
                    f"Processed {processed}/{total_articles} articles, "
                    f"Cache hits: {cache_hits}, API calls: {api_calls}"
                )
                
                # Delay between API calls (only if not from cache)
                if not self.cache.exists(article_id) or force_re_extract:
                    if idx < len(batch_articles) - 1:  # Don't delay after last article in batch
                        time.sleep(delay_between_calls)
            
            # Save cache after each batch
            self.cache.save()
            
            # Delay between batches (except after last batch)
            if batch_end < total_articles:
                logger.info(f"Waiting {delay_between_batches}s before next batch...")
                time.sleep(delay_between_batches)
        
        logger.info("Batch extraction completed")
        return all_results
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        
        # Calculate average relationships per article
        if stats["total_articles_processed"] > 0:
            stats["average_relationships_per_article"] = (
                stats["total_relationships_extracted"] / stats["total_articles_processed"]
            )
        else:
            stats["average_relationships_per_article"] = 0.0
        
        return stats
    
    def estimate_cost(self, input_chars: int, output_chars: int) -> float:
        """Estimate API cost based on token usage.
        
        Args:
            input_chars: Total input characters
            output_chars: Total output characters
            
        Returns:
            Estimated cost in USD
        """
        # Rough estimate: 4 characters per token
        input_tokens = input_chars / 4
        output_tokens = output_chars / 4
        
        # Gemini 1.5 Flash pricing (as of 2024)
        input_cost_per_1M = 0.075
        output_cost_per_1M = 0.30
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1M
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1M
        
        return input_cost + output_cost

