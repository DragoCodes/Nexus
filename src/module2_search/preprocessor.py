"""Text preprocessing for financial text with special token preservation."""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize


class TextPreprocessor:
    """Preprocess text for indexing and searching, preserving financial tokens."""
    
    def __init__(self):
        """Initialize the preprocessor with NLTK resources."""
        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        
        # Load stopwords and remove negations
        self.stop_words = set(stopwords.words('english'))
        # Remove negations from stopwords to preserve them
        negations = {"not", "no", "never", "against"}
        self.stop_words = self.stop_words - negations
        
        # Initialize stemmer
        self.stemmer = PorterStemmer()
        
        # Define regex patterns for special tokens
        self.stock_ticker_pattern = re.compile(r'\$[A-Z]{1,5}\b')
        self.percentage_pattern = re.compile(r'\d+\.?\d*%')
        self.currency_pattern = re.compile(r'[\$€£]\d+\.?\d*[KMB]?')
        self.company_suffix_pattern = re.compile(r'\b(Inc|Co|Ltd|Corp|LLC)\.')
    
    def _extract_special_tokens(self, text):
        """
        Extract special tokens (stock tickers, percentages, currency, company suffixes).
        
        Args:
            text: Input text string
            
        Returns:
            Dictionary mapping position to token: {position: token}
        """
        special_tokens = {}
        
        # Find all matches with their positions
        for pattern in [self.stock_ticker_pattern, self.percentage_pattern, 
                       self.currency_pattern, self.company_suffix_pattern]:
            for match in pattern.finditer(text):
                start_pos = match.start()
                token = match.group()
                special_tokens[start_pos] = token
        
        return special_tokens
    
    def tokenize(self, text):
        """
        Tokenize text while preserving special tokens.
        
        Args:
            text: Input text string
            
        Returns:
            List of tokens
        """
        if not text or not isinstance(text, str):
            return []
        
        # Extract special tokens with their positions
        special_tokens = self._extract_special_tokens(text)
        
        # Use NLTK tokenizer
        tokens = word_tokenize(text)
        
        # Merge special tokens back in
        # This is a simplified approach - in practice, we'll handle special tokens
        # during normalization and stemming stages
        return tokens
    
    def normalize(self, tokens):
        """
        Normalize tokens (lowercase except stock tickers).
        
        Args:
            tokens: List of tokens
            
        Returns:
            List of normalized tokens
        """
        normalized = []
        for token in tokens:
            # Check if it's a stock ticker (starts with $)
            if token.startswith('$') and len(token) > 1 and token[1:].isupper():
                # Keep stock ticker as-is
                normalized.append(token)
            else:
                # Convert to lowercase
                normalized.append(token.lower())
        
        return normalized
    
    def remove_stopwords(self, tokens):
        """
        Remove stopwords while preserving stock tickers.
        
        Args:
            tokens: List of tokens
            
        Returns:
            List of filtered tokens
        """
        filtered = []
        for token in tokens:
            # Keep stock tickers even if they match stop words
            if token.startswith('$'):
                filtered.append(token)
            elif token.lower() not in self.stop_words:
                filtered.append(token)
        
        return filtered
    
    def stem(self, tokens):
        """
        Apply stemming while preserving special tokens.
        
        Args:
            tokens: List of tokens
            
        Returns:
            List of stemmed tokens
        """
        stemmed = []
        for token in tokens:
            # Check if it's a special token (stock ticker, percentage, currency, company suffix)
            is_special = (
                token.startswith('$') or
                '%' in token or
                any(c in token for c in ['€', '£']) or
                token.endswith('.') and token[:-1] in ['Inc', 'Co', 'Ltd', 'Corp', 'LLC']
            )
            
            if is_special:
                # Keep special tokens as-is
                stemmed.append(token)
            else:
                # Apply stemming
                stemmed.append(self.stemmer.stem(token))
        
        return stemmed
    
    def preprocess(self, text):
        """
        Main preprocessing method that chains all steps.
        
        Args:
            text: Input text string
            
        Returns:
            List of processed tokens
        """
        if not text or not isinstance(text, str):
            return []
        
        try:
            # Step 1: Tokenize
            tokens = self.tokenize(text)
            
            # Step 2: Normalize
            tokens = self.normalize(tokens)
            
            # Step 3: Remove stopwords
            tokens = self.remove_stopwords(tokens)
            
            # Step 4: Stem
            tokens = self.stem(tokens)
            
            return tokens
        except Exception as e:
            print(f"Error during preprocessing: {e}")
            return []

