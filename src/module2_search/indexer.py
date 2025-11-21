"""Inverted index builder for the search engine."""

import pickle
from collections import Counter


class InvertedIndex:
    """Build and manage an inverted index from the corpus."""
    
    def __init__(self, preprocessor):
        """
        Initialize the inverted index.
        
        Args:
            preprocessor: TextPreprocessor instance
        """
        self.preprocessor = preprocessor
        self.index = {}  # {term: [(doc_id, term_freq), ...]}
        self.doc_lengths = {}  # {doc_id: length}
        self.avg_doc_length = 0
        self.num_docs = 0
    
    def build_from_db(self, db_handler):
        """
        Build inverted index from database articles.
        
        Args:
            db_handler: Database handler instance with get_all_articles() method
        """
        print("Fetching articles from database...")
        articles = db_handler.get_all_articles()
        
        if not articles:
            print("No articles found in database!")
            return
        
        print(f"Found {len(articles)} articles. Building index...")
        
        # Build index
        for idx, article in enumerate(articles):
            doc_id = article['article_id']
            
            # Combine headline and full_text
            headline = article.get('headline', '')
            full_text = article.get('full_text', '')
            text = f"{headline} {full_text}".strip()
            
            # Preprocess text
            tokens = self.preprocessor.preprocess(text)
            
            # Store document length
            self.doc_lengths[doc_id] = len(tokens)
            
            # Count term frequencies
            term_freqs = Counter(tokens)
            
            # Update inverted index
            for term, freq in term_freqs.items():
                if term not in self.index:
                    self.index[term] = []
                self.index[term].append((doc_id, freq))
            
            # Log progress every 50 articles
            if (idx + 1) % 50 == 0:
                print(f"Processed {idx + 1}/{len(articles)} articles...")
        
        # Calculate statistics
        self.num_docs = len(articles)
        if self.num_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.num_docs
        
        # Print final statistics
        print(f"\nIndex build complete!")
        print(f"Total documents: {self.num_docs}")
        print(f"Unique terms: {len(self.index)}")
        print(f"Average document length: {self.avg_doc_length:.2f} tokens")
    
    def get_postings(self, term):
        """
        Get posting list for a term.
        
        Args:
            term: Term to look up
            
        Returns:
            List of (doc_id, term_freq) tuples
        """
        return self.index.get(term, [])
    
    def get_document_frequency(self, term):
        """
        Get document frequency for a term.
        
        Args:
            term: Term to look up
            
        Returns:
            Number of documents containing this term
        """
        return len(self.index.get(term, []))
    
    def save_to_disk(self, filepath):
        """
        Save index to disk using pickle.
        
        Args:
            filepath: Path to save the index
        """
        try:
            data = {
                'index': self.index,
                'doc_lengths': self.doc_lengths,
                'avg_doc_length': self.avg_doc_length,
                'num_docs': self.num_docs
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            
            import os
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # Size in MB
            print(f"Index saved to {filepath}")
            print(f"File size: {file_size:.2f} MB")
        except Exception as e:
            print(f"Error saving index: {e}")
            raise
    
    def load_from_disk(self, filepath):
        """
        Load index from disk.
        
        Args:
            filepath: Path to load the index from
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.index = data['index']
            self.doc_lengths = data['doc_lengths']
            self.avg_doc_length = data['avg_doc_length']
            self.num_docs = data['num_docs']
            
            print(f"Index loaded from {filepath}")
            print(f"Total documents: {self.num_docs}")
            print(f"Unique terms: {len(self.index)}")
            print(f"Average document length: {self.avg_doc_length:.2f} tokens")
        except Exception as e:
            print(f"Error loading index: {e}")
            raise

