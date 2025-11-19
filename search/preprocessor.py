"""
Text Preprocessor for Financial Documents
Handles tokenization, normalization, stemming, and special token preservation
"""
import re
import nltk
from typing import List, Set
import string

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


class FinancialTextPreprocessor:
    def __init__(self, 
                 remove_stopwords: bool = True,
                 apply_stemming: bool = True,
                 preserve_special_tokens: bool = True):
        """
        Initialize preprocessor with configurable options
        
        Args:
            remove_stopwords: Remove common English stopwords
            apply_stemming: Apply Porter stemming algorithm
            preserve_special_tokens: Keep stock tickers, currencies
        """
        self.remove_stopwords = remove_stopwords
        self.apply_stemming = apply_stemming
        self.preserve_special_tokens = preserve_special_tokens
        
        self.stop_words = set(stopwords.words('english'))
        self.stemmer = PorterStemmer()
        
        # Financial-specific stopwords to keep
        self.keep_words = {
            'not', 'no', 'nor', 'up', 'down', 'over', 'under',
            'above', 'below', 'more', 'most', 'against'
        }
        self.stop_words = self.stop_words - self.keep_words
        
        # Patterns for special tokens
        self.stock_ticker_pattern = re.compile(r'\$[A-Z]{1,5}\b')
        self.currency_pattern = re.compile(r'[$€£¥₹]\d+[BMK]?')
        self.percentage_pattern = re.compile(r'\d+\.?\d*%')
    
    def preprocess(self, text: str) -> List[str]:
        """
        Full preprocessing pipeline
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            List of processed tokens
        """
        # Step 1: Extract and preserve special tokens
        special_tokens = []
        if self.preserve_special_tokens:
            special_tokens = self._extract_special_tokens(text)
        
        # Step 2: Lowercase normalization
        text = text.lower()
        
        # Step 3: Remove punctuation (except in special tokens)
        text = self._clean_punctuation(text)
        
        # Step 4: Tokenization
        tokens = word_tokenize(text)
        
        # Step 5: Filter stopwords
        if self.remove_stopwords:
            tokens = [t for t in tokens if t not in self.stop_words]
        
        # Step 6: Apply stemming
        if self.apply_stemming:
            tokens = [self.stemmer.stem(t) for t in tokens]
        
        # Step 7: Filter out very short tokens and numbers
        tokens = [t for t in tokens if len(t) > 2 and not t.isdigit()]
        
        # Step 8: Add back special tokens
        tokens.extend(special_tokens)
        
        return tokens
    
    def _extract_special_tokens(self, text: str) -> List[str]:
        """Extract stock tickers, currencies, percentages"""
        special = []
        
        # Stock tickers (e.g., $NVDA, $AAPL)
        tickers = self.stock_ticker_pattern.findall(text)
        special.extend([t.lower() for t in tickers])
        
        # Currency amounts (e.g., $100M, €50B)
        currencies = self.currency_pattern.findall(text)
        special.extend([c.lower() for c in currencies])
        
        # Percentages (e.g., 25%, 3.5%)
        percentages = self.percentage_pattern.findall(text)
        special.extend([p.lower() for p in percentages])
        
        return special
    
    def _clean_punctuation(self, text: str) -> str:
        """Remove punctuation but preserve hyphens in compound words"""
        # Keep hyphens between words (e.g., "state-of-the-art")
        text = re.sub(r'(\w)-(\w)', r'\1\2', text)
        
        # Remove other punctuation
        translator = str.maketrans('', '', string.punctuation)
        return text.translate(translator)
    
    def preprocess_query(self, query: str) -> List[str]:
        """Preprocess a search query (same as document preprocessing)"""
        return self.preprocess(query)
    
    def batch_preprocess(self, texts: List[str]) -> List[List[str]]:
        """Preprocess multiple texts efficiently"""
        return [self.preprocess(text) for text in texts]


# Quick test
if __name__ == "__main__":
    preprocessor = FinancialTextPreprocessor()
    
    test_texts = [
        "Apple Inc. announced a $100B stock buyback program, sending $AAPL up 5%.",
        "NVIDIA partners with TSMC for 3nm chip manufacturing technology.",
        "The company's Q3 earnings exceeded expectations with 25% growth."
    ]
    
    print("Preprocessing Examples:\n")
    for text in test_texts:
        tokens = preprocessor.preprocess(text)
        print(f"Original: {text}")
        print(f"Tokens: {tokens}")
        print()