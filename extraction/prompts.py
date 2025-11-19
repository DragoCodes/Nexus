"""
Prompt Templates for Entity and Relationship Extraction
"""

SYSTEM_PROMPT = """You are a financial information extraction AI. Your task is to extract structured relationship triples from financial news articles.

Extract entities (companies, people, products) and the relationships between them. Focus on:
- Corporate relationships (partnerships, acquisitions, supply chains)
- Business actions (invests, acquires, supplies, manufactures)
- Leadership and personnel (CEO of, founder of, joins)
- Product relationships (produces, develops, launches)

Return ONLY a valid JSON array. Each object must have exactly these fields:
{
  "entity1": "First entity name",
  "entity1_type": "Company|Person|Product",
  "relationship": "relationship_type",
  "entity2": "Second entity name",
  "entity2_type": "Company|Person|Product",
  "confidence": 0.0-1.0
}

Rules:
- Use snake_case for relationship types (e.g., "partners_with", "acquires", "supplies_to")
- Entity names should be clean (e.g., "NVIDIA" not "NVIDIA Corporation")
- Only extract explicit relationships mentioned in the text
- Confidence: 1.0 for direct statements, 0.8 for implied, 0.6 for speculative
- Return empty array [] if no relationships found
- Do NOT include markdown, explanations, or any text outside the JSON array"""


FEW_SHOT_EXAMPLES = """
Example 1:
Text: "Apple Inc. announced today that it has acquired AI startup Emotient for approximately $100 million."
Output:
[
  {
    "entity1": "Apple",
    "entity1_type": "Company",
    "relationship": "acquires",
    "entity2": "Emotient",
    "entity2_type": "Company",
    "confidence": 1.0
  }
]

Example 2:
Text: "NVIDIA partners with TSMC for advanced 3nm chip manufacturing. CEO Jensen Huang praised the collaboration."
Output:
[
  {
    "entity1": "NVIDIA",
    "entity1_type": "Company",
    "relationship": "partners_with",
    "entity2": "TSMC",
    "entity2_type": "Company",
    "confidence": 1.0
  },
  {
    "entity1": "NVIDIA",
    "entity1_type": "Company",
    "relationship": "manufactures_with",
    "entity2": "TSMC",
    "entity2_type": "Company",
    "confidence": 1.0
  },
  {
    "entity1": "Jensen Huang",
    "entity1_type": "Person",
    "relationship": "ceo_of",
    "entity2": "NVIDIA",
    "entity2_type": "Company",
    "confidence": 1.0
  }
]

Example 3:
Text: "Microsoft reported strong quarterly earnings but did not announce any major deals."
Output:
[]
"""


def create_extraction_prompt(article_text: str) -> str:
    """
    Create the full prompt for extraction
    
    Args:
        article_text: The article text to extract from
        
    Returns:
        Formatted prompt string
    """
    user_prompt = f"""Extract relationship triples from this financial news article:

{article_text}

Remember: Return ONLY a valid JSON array of relationship objects. No markdown, no explanations."""
    
    return user_prompt


def create_messages(article_text: str) -> list:
    """
    Create the messages array for OpenAI-compatible API
    
    Args:
        article_text: The article text to extract from
        
    Returns:
        List of message dicts
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\n" + FEW_SHOT_EXAMPLES
        },
        {
            "role": "user",
            "content": create_extraction_prompt(article_text)
        }
    ]


# Validation schema
EXPECTED_FIELDS = {
    "entity1": str,
    "entity1_type": str,
    "relationship": str,
    "entity2": str,
    "entity2_type": str,
    "confidence": (int, float)
}

VALID_ENTITY_TYPES = {"Company", "Person", "Product"}


def validate_triple(triple: dict) -> bool:
    """
    Validate a single triple object
    
    Args:
        triple: Dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check all required fields present
    for field, expected_type in EXPECTED_FIELDS.items():
        if field not in triple:
            return False
        
        if not isinstance(triple[field], expected_type):
            return False
    
    # Validate entity types
    if triple["entity1_type"] not in VALID_ENTITY_TYPES:
        return False
    
    if triple["entity2_type"] not in VALID_ENTITY_TYPES:
        return False
    
    # Validate confidence range
    if not (0.0 <= triple["confidence"] <= 1.0):
        return False
    
    return True


# Quick test
if __name__ == "__main__":
    sample_text = "NVIDIA announced a partnership with TSMC for chip manufacturing."
    
    messages = create_messages(sample_text)
    
    print("System Prompt:")
    print(messages[0]["content"][:200] + "...\n")
    
    print("User Prompt:")
    print(messages[1]["content"])