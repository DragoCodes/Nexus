"""BM25 scoring implementation for document ranking."""

import math


class BM25Scorer:
    """Calculate BM25 scores for documents."""
    
    def __init__(self, inverted_index, k1=1.5, b=0.75):
        """
        Initialize BM25 scorer.
        
        Args:
            inverted_index: InvertedIndex instance
            k1: BM25 tuning parameter (default: 1.5)
            b: BM25 tuning parameter (default: 0.75)
        """
        self.inverted_index = inverted_index
        self.k1 = k1
        self.b = b
    
    def calculate_idf(self, term):
        """
        Calculate IDF score for a term.
        
        Formula: IDF(term) = log((N - n(term) + 0.5) / (n(term) + 0.5) + 1)
        
        Args:
            term: Term to calculate IDF for
            
        Returns:
            IDF score
        """
        N = self.inverted_index.num_docs
        n_term = self.inverted_index.get_document_frequency(term)
        
        if n_term == 0:
            return 0
        
        # Calculate IDF
        idf = math.log((N - n_term + 0.5) / (n_term + 0.5) + 1)
        return idf
    
    def calculate_bm25_for_document(self, query_terms, doc_id):
        """
        Calculate BM25 score for a single document given query terms.
        
        Args:
            query_terms: List of query terms
            doc_id: Document ID to score
            
        Returns:
            BM25 score for the document
        """
        score = 0.0
        
        # Get document length
        doc_length = self.inverted_index.doc_lengths.get(doc_id, 0)
        if doc_length == 0:
            return 0.0
        
        avg_doc_length = self.inverted_index.avg_doc_length
        
        # Calculate score for each query term
        for term in query_terms:
            # Get IDF for this term
            idf = self.calculate_idf(term)
            
            # Get term frequency in this document
            term_freq = 0
            postings = self.inverted_index.get_postings(term)
            for posting_doc_id, posting_freq in postings:
                if posting_doc_id == doc_id:
                    term_freq = posting_freq
                    break
            
            # If term not in document, skip
            if term_freq == 0:
                continue
            
            # Calculate BM25 component
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * (
                1 - self.b + self.b * (doc_length / avg_doc_length)
            )
            
            score += idf * (numerator / denominator)
        
        return score
    
    def score_all_documents(self, query_terms):
        """
        Score all documents that contain at least one query term.
        
        Args:
            query_terms: List of query terms
            
        Returns:
            Dictionary mapping doc_id to BM25 score: {doc_id: score}
        """
        # Find all documents that contain any query term
        relevant_docs = set()
        for term in query_terms:
            postings = self.inverted_index.get_postings(term)
            for doc_id, _ in postings:
                relevant_docs.add(doc_id)
        
        # Calculate BM25 score for each relevant document
        scores = {}
        for doc_id in relevant_docs:
            score = self.calculate_bm25_for_document(query_terms, doc_id)
            if score > 0:
                scores[doc_id] = score
        
        return scores

