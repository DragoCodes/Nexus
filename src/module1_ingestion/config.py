"""Configuration management for Module 1."""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# News API Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"

# Local Database Configuration (SQLite)
# Database will be stored locally in data/articles.db
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "data" / "articles.db"))


def validate_config():
    """Validate that all required configuration variables are set.
    
    Raises:
        ValueError: If any required configuration is missing.
    """
    missing_vars = []
    
    if not NEWS_API_KEY:
        missing_vars.append("NEWS_API_KEY")
    
    if missing_vars:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set these variables in your .env file.\n"
            f"Example .env file location: config/.env or project root/.env"
        )
        raise ValueError(error_msg)
    
    return True

