"""Parse and validate LLM extraction responses."""
import json
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ExtractionParser:
    """Parse and validate LLM responses."""
    
    def __init__(self, allowed_relationship_types: List[str], allowed_entity_types: List[str]):
        """Initialize parser with validation rules.
        
        Args:
            allowed_relationship_types: List of valid relationship types
            allowed_entity_types: List of valid entity types
        """
        self.allowed_relationship_types = [rt.lower() for rt in allowed_relationship_types]
        self.allowed_entity_types = allowed_entity_types
        self.stats = {
            "total_received": 0,
            "valid": 0,
            "invalid": 0
        }
        logger.info("Initialized ExtractionParser")
    
    def parse(self, llm_response: Optional[str]) -> Optional[List[Dict]]:
        """Parse LLM response into list of relationships.
        
        Args:
            llm_response: Raw response from LLM (may contain markdown or extra text)
            
        Returns:
            List of validated relationship dictionaries, or None if parsing fails
        """
        if not llm_response:
            logger.warning("Empty LLM response received")
            return None
        
        # Try to extract JSON from response
        json_text = self._extract_json(llm_response)
        
        if not json_text:
            logger.error("Could not extract JSON from LLM response")
            return None
        
        # Parse JSON
        try:
            parsed_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.debug(f"Failed JSON text: {json_text[:500]}")
            return None
        
        # Validate and return
        validated = self.validate_extractions(parsed_data)
        return validated
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON array from text that may contain markdown or extra content.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON string, or None if not found
        """
        # Strip whitespace
        text = text.strip()
        
        # Try direct parsing first
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array in markdown code blocks
        json_patterns = [
            r'```json\s*(\[.*?\])\s*```',  # ```json [...] ```
            r'```\s*(\[.*?\])```',  # ``` [...] ```
            r'(\[.*?\])',  # Just find array
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_candidate = match.group(1)
                try:
                    json.loads(json_candidate)
                    return json_candidate
                except json.JSONDecodeError:
                    continue
        
        # Try to find array boundaries
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = text[start_idx:end_idx + 1]
            try:
                json.loads(json_candidate)
                return json_candidate
            except json.JSONDecodeError:
                pass
        
        return None
    
    def validate_extractions(self, extractions_list: any) -> List[Dict]:
        """Validate list of extractions.
        
        Args:
            extractions_list: List or other data structure from parsed JSON
            
        Returns:
            List of valid relationship dictionaries
        """
        self.stats["total_received"] += 1
        
        # Check if it's a list
        if not isinstance(extractions_list, list):
            logger.warning(f"Expected list, got {type(extractions_list)}")
            self.stats["invalid"] += 1
            return []
        
        valid_relationships = []
        invalid_count = 0
        invalid_reasons = []
        
        for idx, rel_obj in enumerate(extractions_list):
            if not isinstance(rel_obj, dict):
                invalid_count += 1
                invalid_reasons.append(f"Item {idx}: not a dictionary")
                continue
            
            # Normalize relationship
            normalized = self.normalize_relationship(rel_obj)
            
            # Validate required fields
            required_fields = ["entity1", "entity1_type", "relationship", "entity2", "entity2_type"]
            missing_fields = [field for field in required_fields if field not in normalized or not normalized[field]]
            
            if missing_fields:
                invalid_count += 1
                invalid_reasons.append(f"Item {idx}: missing fields {missing_fields}")
                continue
            
            # Validate entity types
            if normalized["entity1_type"] not in self.allowed_entity_types:
                invalid_count += 1
                invalid_reasons.append(
                    f"Item {idx}: invalid entity1_type '{normalized['entity1_type']}'"
                )
                continue
            
            if normalized["entity2_type"] not in self.allowed_entity_types:
                invalid_count += 1
                invalid_reasons.append(
                    f"Item {idx}: invalid entity2_type '{normalized['entity2_type']}'"
                )
                continue
            
            # Validate relationship type
            rel_type_lower = normalized["relationship"].lower()
            if rel_type_lower not in self.allowed_relationship_types:
                invalid_count += 1
                invalid_reasons.append(
                    f"Item {idx}: invalid relationship type '{normalized['relationship']}'"
                )
                continue
            
            # Check self-relationships
            if normalized["entity1"].lower().strip() == normalized["entity2"].lower().strip():
                invalid_count += 1
                invalid_reasons.append(f"Item {idx}: self-relationship (entity1 == entity2)")
                continue
            
            # All validations passed
            valid_relationships.append(normalized)
        
        if invalid_count > 0:
            logger.debug(
                f"Filtered out {invalid_count} invalid relationships. "
                f"Reasons: {', '.join(invalid_reasons[:5])}"
            )
        
        self.stats["valid"] += len(valid_relationships)
        self.stats["invalid"] += invalid_count
        
        return valid_relationships
    
    def normalize_relationship(self, rel_obj: Dict) -> Dict:
        """Normalize relationship object.
        
        Args:
            rel_obj: Raw relationship dictionary
            
        Returns:
            Normalized relationship dictionary
        """
        normalized = {}
        
        # Normalize relationship type (lowercase with underscores)
        if "relationship" in rel_obj:
            rel_type = str(rel_obj["relationship"]).lower().replace(" ", "_")
            normalized["relationship"] = rel_type
        else:
            normalized["relationship"] = rel_obj.get("relationship", "")
        
        # Normalize entity types (capitalize first letter)
        for field in ["entity1_type", "entity2_type"]:
            if field in rel_obj:
                entity_type = str(rel_obj[field]).strip()
                if entity_type:
                    normalized[field] = entity_type[0].upper() + entity_type[1:].lower()
                else:
                    normalized[field] = entity_type
            else:
                normalized[field] = rel_obj.get(field, "")
        
        # Trim whitespace from entity names
        for field in ["entity1", "entity2"]:
            if field in rel_obj:
                normalized[field] = str(rel_obj[field]).strip()
            else:
                normalized[field] = rel_obj.get(field, "")
        
        return normalized
    
    def get_statistics(self) -> Dict:
        """Get parsing statistics."""
        return self.stats.copy()

