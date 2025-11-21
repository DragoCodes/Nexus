"""News API client for fetching articles."""
import time
import logging
import requests
from typing import Optional, List, Dict

from .config import NEWS_API_KEY, NEWS_API_BASE_URL

logger = logging.getLogger(__name__)


class NewsAPIClient:
    """Client for interacting with News API."""
    
    def __init__(self, api_key: str):
        """Initialize News API client.
        
        Args:
            api_key: News API key
        """
        self.api_key = api_key
        self.base_url = NEWS_API_BASE_URL
        self.session = requests.Session()
        logger.info("Initialized NewsAPIClient")
    
    def _make_request(self, params: Dict, max_retries: int = 3) -> Dict:
        """Make HTTP GET request to News API with retry logic.
        
        Args:
            params: Query parameters for the API request
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response from the API
            
        Raises:
            requests.RequestException: If request fails after all retries
            ValueError: If API returns an error status
        """
        params["apiKey"] = self.api_key
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Making API request (attempt {attempt + 1}/{max_retries}): {params.get('q', 'N/A')}")
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=30
                )
                
                # Handle HTTP status codes
                if response.status_code == 401:
                    error_msg = "Invalid API key. Please check your NEWS_API_KEY in .env file"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = 60
                        logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "Rate limit exceeded. Please wait before making more requests"
                        logger.error(error_msg)
                        raise requests.RequestException(error_msg)
                
                elif response.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = 10
                        logger.warning(f"Server error {response.status_code}, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"Server error: {response.status_code}"
                        logger.error(error_msg)
                        raise requests.RequestException(error_msg)
                
                # Parse JSON response
                response.raise_for_status()
                json_response = response.json()
                
                # Check for error status in JSON response
                if json_response.get("status") == "error":
                    error_msg = f"API returned error: {json_response.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                return json_response
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 5
                    logger.warning(f"Network error: {str(e)}, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {str(e)}")
                    raise
        
        raise requests.RequestException(f"Request failed after {max_retries} attempts")
    
    def fetch_articles(
        self,
        query: str,
        page: int = 1,
        page_size: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict]:
        """Fetch articles from News API for a given query.
        
        Args:
            query: Search query string
            page: Page number (starts at 1)
            page_size: Number of articles per page (max 100)
            from_date: Start date in YYYY-MM-DD format (optional)
            to_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            List of article dictionaries from the API
        """
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "page": page,
            "pageSize": min(page_size, 100)  # API max is 100
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        logger.info(f"Fetching articles for query: '{query}', page: {page}")
        
        try:
            response = self._make_request(params)
            articles = response.get("articles", [])
            total_results = response.get("totalResults", 0)
            logger.info(f"Fetched {len(articles)} articles (total available: {total_results})")
            return articles
        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []
    
    def fetch_all_articles_for_query(
        self,
        query: str,
        max_articles: int = 1000,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict]:
        """Fetch multiple pages of articles until max_articles is reached or no more results.
        
        Args:
            query: Search query string
            max_articles: Maximum number of articles to fetch
            from_date: Start date in YYYY-MM-DD format (optional)
            to_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            List of all collected article dictionaries
        """
        all_articles = []
        page = 1
        page_size = 100
        
        logger.info(f"Fetching up to {max_articles} articles for query: '{query}'")
        
        while len(all_articles) < max_articles:
            articles = self.fetch_articles(
                query=query,
                page=page,
                page_size=page_size,
                from_date=from_date,
                to_date=to_date
            )
            
            if not articles:
                logger.info(f"No more articles found at page {page}")
                break
            
            all_articles.extend(articles)
            logger.info(f"Fetched page {page}, total articles collected: {len(all_articles)}")
            
            # If we got fewer articles than page_size, we've reached the end
            if len(articles) < page_size:
                logger.info(f"Reached end of results (got {len(articles)} articles on page {page})")
                break
            
            # Check if we've reached max_articles
            if len(all_articles) >= max_articles:
                logger.info(f"Reached max_articles limit: {max_articles}")
                break
            
            # Increment page and add delay to respect rate limits
            page += 1
            time.sleep(1)  # 1 second delay between requests
        
        # Trim to max_articles if we exceeded it
        if len(all_articles) > max_articles:
            all_articles = all_articles[:max_articles]
        
        logger.info(f"Finished fetching articles for query '{query}': {len(all_articles)} total")
        return all_articles

