"""Data models for type safety and consistency."""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ArticleSearchResult(BaseModel):
    """Search result for an article."""
    
    article_id: str
    score: float
    headline: str
    publication_date: datetime
    source: str
    url: str


class EntityDetails(BaseModel):
    """Detailed information about an entity in the knowledge graph."""
    
    entity_name: str
    entity_type: str
    mention_count: int
    incoming_relationships: List[Dict] = Field(default_factory=list)
    outgoing_relationships: List[Dict] = Field(default_factory=list)
    total_degree: int = 0


class PageRankResult(BaseModel):
    """PageRank result for an entity."""
    
    entity_name: str
    entity_type: str
    score: float
    rank: int


class Community(BaseModel):
    """A detected community in the knowledge graph."""
    
    community_id: int
    entities: List[str] = Field(default_factory=list)
    size: int
    dominant_types: Dict[str, int] = Field(default_factory=dict)
    description: str = ""


class TrendDataPoint(BaseModel):
    """A single data point in a trend analysis."""
    
    date: str
    count: int
    relationship_type: str


class NetworkStatistics(BaseModel):
    """Overall network statistics for the knowledge graph."""
    
    total_entities: int
    total_relationships: int
    average_degree: float
    density: float
    description: str = ""

