"""Search engine interface for querying articles."""

from .bm25_scorer import BM25Scorer


class SearchEngine:
    """Provide search interface for articles."""
    
    def __init__(self, inverted_index, db_handler, preprocessor):
        """
        Initialize search engine.
        
        Args:
            inverted_index: InvertedIndex instance
            db_handler: Database handler instance
            preprocessor: TextPreprocessor instance
        """
        self.inverted_index = inverted_index
        self.db_handler = db_handler
        self.preprocessor = preprocessor
    
    def search(self, query, k=10):
        """
        Search for articles matching the query.
        
        Args:
            query: Search query string
            k: Number of top results to return (default: 10)
            
        Returns:
            List of result dictionaries with article metadata and scores
        """
        # Preprocess query
        query_terms = self.preprocessor.preprocess(query)
        
        # If no valid terms after preprocessing, return empty list
        if not query_terms:
            return []
        
        # Create BM25 scorer
        scorer = BM25Scorer(self.inverted_index)
        
        # Get scores for all documents
        scores = scorer.score_all_documents(query_terms)
        
        # If no documents match, return empty list
        if not scores:
            return []
        
        # Sort documents by score (descending)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take top-k documents
        top_doc_ids = [doc_id for doc_id, score in sorted_scores[:k]]
        
        # Create score lookup
        score_lookup = {doc_id: score for doc_id, score in sorted_scores}
        
        # Fetch article metadata from database
        try:
            # Use db_handler to fetch articles
            articles = self.db_handler.get_articles_by_ids(top_doc_ids)
            
            # Format results
            results = []
            for article in articles:
                article_id = article['article_id']
                results.append({
                    "article_id": article_id,
                    "score": score_lookup.get(article_id, 0.0),
                    "headline": article.get('headline', ''),
                    "publication_date": article.get('publication_date', ''),
                    "source": article.get('source', ''),
                    "url": article.get('url', '')
                })
            
            # Sort by score (in case database returned in different order)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return results
        except Exception as e:
            print(f"Error fetching articles from database: {e}")
            return []

