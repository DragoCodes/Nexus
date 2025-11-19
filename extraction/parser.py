"""
LLM response parser and validation helpers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError, field_validator


class TripleModel(BaseModel):
    entity1: str = Field(..., min_length=1)
    entity1_type: str = Field(..., pattern="^(Company|Person|Product)$")
    relationship: str = Field(..., min_length=2)
    entity2: str = Field(..., min_length=1)
    entity2_type: str = Field(..., pattern="^(Company|Person|Product)$")
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("relationship")
    @classmethod
    def enforce_snake_case(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    @field_validator("entity1", "entity2", mode="before")
    @classmethod
    def strip_entities(cls, value: str) -> str:
        return value.strip()


class ExtractionModel(BaseModel):
    article_id: str
    extracted_at: str
    triples: List[TripleModel]
    metadata: Dict[str, Any] = Field(default_factory=dict)


def parse_llm_response(article_id: str, raw_response: str, metadata: Dict | None = None) -> Dict:
    """
    Parse the LLM JSON response into validated structure.
    """
    metadata = metadata or {}
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from LLM: {exc}") from exc

    if isinstance(parsed, dict) and "triples" in parsed:
        triples_payload = parsed["triples"]
    elif isinstance(parsed, list):
        triples_payload = parsed
    else:
        raise ValueError("LLM response must be a list or dict with 'triples'.")

    model = ExtractionModel(
        article_id=article_id,
        extracted_at=datetime.now(tz=timezone.utc).isoformat(),
        triples=triples_payload,
        metadata=metadata,
    )
    return model.model_dump()
