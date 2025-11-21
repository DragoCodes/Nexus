"""Prompt template management for relationship extraction."""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class PromptManager:
    """Manage prompt templates and formatting for extraction."""
    
    # Allowed relationship types
    RELATIONSHIP_TYPES = [
        "acquires", "acquired_by",
        "partners_with",
        "invests_in", "receives_investment_from",
        "supplies_to", "sources_from",
        "competes_with",
        "employs", "works_for", "appoints",
        "owns", "owned_by",
        "sues", "sued_by",
        "regulates", "regulated_by",
        "announces",
        "launches",
        "merges_with"
    ]
    
    # Allowed entity types
    ENTITY_TYPES = ["Company", "Person", "Product", "Organization", "Location"]
    
    def __init__(self):
        """Initialize prompt manager with base template."""
        self.base_prompt = self._build_base_prompt()
        logger.info("Initialized PromptManager")
    
    def _build_base_prompt(self) -> str:
        """Build the base prompt template."""
        return """You are a financial information extraction system. Your task is to extract explicit relationships between entities from financial news articles.

ENTITY TYPES:
- Company: Business corporations, firms, enterprises
- Person: Individuals (CEOs, executives, investors, etc.)
- Product: Products, services, or offerings
- Organization: Non-corporate organizations (governments, agencies, institutions)
- Location: Geographic locations (cities, countries, regions)

RELATIONSHIP TYPES (use exact names):
- acquires / acquired_by
- partners_with
- invests_in / receives_investment_from
- supplies_to / sources_from
- competes_with
- employs / works_for / appoints
- owns / owned_by
- sues / sued_by
- regulates / regulated_by
- announces
- launches
- merges_with

OUTPUT FORMAT:
Return ONLY a JSON array. No markdown. No explanation.
Each relationship must have exactly these fields:
{{
  "entity1": "exact name from text",
  "entity1_type": "Company|Person|Product|Organization|Location",
  "relationship": "relationship_type",
  "entity2": "exact name from text",
  "entity2_type": "Company|Person|Product|Organization|Location"
}}

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON array, no preamble, no explanation, no markdown formatting
2. If no relationships found, return empty array: []
3. Use exact entity names as they appear in the text
4. Resolve pronouns ("it", "they", "the company") to actual entity names
5. Extract only explicitly stated relationships, not implied ones
6. Maximum 20 relationships per article (prioritize the most important ones)
7. entity1 and entity2 must be different entities
8. Keep JSON compact - no extra whitespace or formatting

EXAMPLES:

Example 1:
Article: "Tesla announced a partnership with Panasonic to build battery factories. The companies will invest $5 billion together."
Output:
[
  {{
    "entity1": "Tesla",
    "entity1_type": "Company",
    "relationship": "partners_with",
    "entity2": "Panasonic",
    "entity2_type": "Company"
  }},
  {{
    "entity1": "Tesla",
    "entity1_type": "Company",
    "relationship": "invests_in",
    "entity2": "battery factories",
    "entity2_type": "Product"
  }},
  {{
    "entity1": "Panasonic",
    "entity1_type": "Company",
    "relationship": "invests_in",
    "entity2": "battery factories",
    "entity2_type": "Product"
  }}
]

Example 2:
Article: "Apple CEO Tim Cook announced the launch of iPhone 15 in San Francisco. The company competes with Samsung."
Output:
[
  {{
    "entity1": "Apple",
    "entity1_type": "Company",
    "relationship": "employs",
    "entity2": "Tim Cook",
    "entity2_type": "Person"
  }},
  {{
    "entity1": "Apple",
    "entity1_type": "Company",
    "relationship": "launches",
    "entity2": "iPhone 15",
    "entity2_type": "Product"
  }},
  {{
    "entity1": "Apple",
    "entity1_type": "Company",
    "relationship": "competes_with",
    "entity2": "Samsung",
    "entity2_type": "Company"
  }}
]

Example 3:
Article: "The Federal Reserve regulates banking institutions."
Output:
[
  {{
    "entity1": "Federal Reserve",
    "entity1_type": "Organization",
    "relationship": "regulates",
    "entity2": "banking institutions",
    "entity2_type": "Organization"
  }}
]

Now extract relationships from the following article:

HEADLINE: {headline}

ARTICLE TEXT:
{article_text}

Return ONLY the JSON array:"""
    
    def _truncate_text(self, text: str, max_words: int = 3000) -> str:
        """Truncate text to maximum word count.
        
        Args:
            text: Text to truncate
            max_words: Maximum number of words (reduced to leave room for response)
            
        Returns:
            Truncated text
        """
        words = text.split()
        if len(words) <= max_words:
            return text
        
        truncated = ' '.join(words[:max_words])
        logger.debug(f"Truncated article from {len(words)} to {max_words} words")
        return truncated + "..."
    
    def generate_extraction_prompt(self, article_text: str, article_headline: str) -> str:
        """Generate extraction prompt for an article.
        
        Args:
            article_text: Full article text
            article_headline: Article headline
            
        Returns:
            Complete formatted prompt
        """
        # Truncate if necessary (reduced to leave room for response)
        truncated_text = self._truncate_text(article_text, max_words=3000)
        
        # Format prompt
        prompt = self.base_prompt.format(
            headline=article_headline,
            article_text=truncated_text
        )
        
        return prompt
    
    def get_relationship_types(self) -> List[str]:
        """Get list of allowed relationship types."""
        return self.RELATIONSHIP_TYPES.copy()
    
    def get_entity_types(self) -> List[str]:
        """Get list of allowed entity types."""
        return self.ENTITY_TYPES.copy()

