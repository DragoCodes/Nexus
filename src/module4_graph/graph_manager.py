"""Graph manager for SQLite database and NetworkX graph synchronization."""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GraphManager:
    """Manage SQLite database and NetworkX graph synchronization."""
    
    def __init__(self, db_path: str = "data/nexus_graph.db"):
        """Initialize GraphManager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.graph = nx.DiGraph()
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        self._create_tables()
        logger.info(f"Initialized GraphManager with database: {db_path}")
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Create entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_name TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Create relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity1 TEXT NOT NULL,
                entity2 TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                source_article_ids TEXT NOT NULL,
                publication_dates TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (entity1) REFERENCES entities(entity_name),
                FOREIGN KEY (entity2) REFERENCES entities(entity_name)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type 
            ON entities(entity_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship_entity1 
            ON relationships(entity1)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship_entity2 
            ON relationships(entity2)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship_type 
            ON relationships(relationship_type)
        """)
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def add_or_update_entity(self, entity_name: str, entity_type: str) -> None:
        """Add or update an entity in the database and graph.
        
        Args:
            entity_name: Name of the entity
            entity_type: Type of entity (Company, Person, Product, etc.)
        """
        entity_name = entity_name.strip()
        entity_type = entity_type.strip()
        now = datetime.utcnow().isoformat()
        
        cursor = self.conn.cursor()
        
        # Check if entity exists
        cursor.execute("SELECT mention_count FROM entities WHERE entity_name = ?", (entity_name,))
        row = cursor.fetchone()
        
        if row:
            # Update existing entity
            new_count = row['mention_count'] + 1
            cursor.execute("""
                UPDATE entities 
                SET mention_count = ?, last_updated = ?
                WHERE entity_name = ?
            """, (new_count, now, entity_name))
            mention_count = new_count
        else:
            # Insert new entity
            cursor.execute("""
                INSERT INTO entities (entity_name, entity_type, mention_count, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_name, entity_type, 1, now, now))
            mention_count = 1
        
        self.conn.commit()
        
        # Update NetworkX graph
        self.graph.add_node(entity_name, type=entity_type, mention_count=mention_count)
        
        logger.debug(f"Added/updated entity: {entity_name} ({entity_type})")
    
    def add_or_update_relationship(
        self,
        entity1: str,
        entity2: str,
        relationship_type: str,
        article_id: str,
        publication_date: str,
        entity1_type: Optional[str] = None,
        entity2_type: Optional[str] = None
    ) -> None:
        """Add or update a relationship in the database and graph.
        
        Args:
            entity1: First entity name
            entity2: Second entity name
            relationship_type: Type of relationship
            article_id: ID of the source article
            publication_date: Publication date of the article (ISO format)
            entity1_type: Type of entity1 (if not provided, will query or use default)
            entity2_type: Type of entity2 (if not provided, will query or use default)
        """
        entity1 = entity1.strip()
        entity2 = entity2.strip()
        relationship_type = relationship_type.strip().lower()
        now = datetime.utcnow().isoformat()
        
        # Ensure both entities exist
        # If entity types not provided, try to get from database or use default
        cursor = self.conn.cursor()
        
        if entity1_type is None:
            cursor.execute("SELECT entity_type FROM entities WHERE entity_name = ?", (entity1,))
            row = cursor.fetchone()
            entity1_type = row['entity_type'] if row else 'Company'
        
        if entity2_type is None:
            cursor.execute("SELECT entity_type FROM entities WHERE entity_name = ?", (entity2,))
            row = cursor.fetchone()
            entity2_type = row['entity_type'] if row else 'Company'
        
        # Add entities if they don't exist
        self.add_or_update_entity(entity1, entity1_type)
        self.add_or_update_entity(entity2, entity2_type)
        
        cursor = self.conn.cursor()
        
        # Check if this exact relationship exists
        cursor.execute("""
            SELECT id, source_article_ids, publication_dates, frequency
            FROM relationships
            WHERE entity1 = ? AND entity2 = ? AND relationship_type = ?
        """, (entity1, entity2, relationship_type))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing relationship
            existing_article_ids = json.loads(row['source_article_ids'])
            existing_dates = json.loads(row['publication_dates'])
            
            # Append new article_id if not already present
            if article_id not in existing_article_ids:
                existing_article_ids.append(article_id)
                existing_dates.append(publication_date)
            
            new_frequency = row['frequency'] + 1
            
            cursor.execute("""
                UPDATE relationships
                SET source_article_ids = ?,
                    publication_dates = ?,
                    frequency = ?,
                    last_updated = ?
                WHERE id = ?
            """, (
                json.dumps(existing_article_ids),
                json.dumps(existing_dates),
                new_frequency,
                now,
                row['id']
            ))
            
            article_ids = existing_article_ids
            dates = existing_dates
            frequency = new_frequency
        else:
            # Insert new relationship
            article_ids = [article_id]
            dates = [publication_date]
            
            cursor.execute("""
                INSERT INTO relationships (
                    entity1, entity2, relationship_type,
                    source_article_ids, publication_dates,
                    frequency, first_seen, last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity1, entity2, relationship_type,
                json.dumps(article_ids),
                json.dumps(dates),
                1, now, now
            ))
            
            frequency = 1
        
        self.conn.commit()
        
        # Update NetworkX graph
        self.graph.add_edge(
            entity1, entity2,
            relationship_type=relationship_type,
            source_article_ids=article_ids,
            publication_dates=dates,
            frequency=frequency
        )
        
        logger.debug(
            f"Added/updated relationship: {entity1} --[{relationship_type}]--> {entity2}"
        )
    
    def load_graph_from_db(self) -> nx.DiGraph:
        """Load graph from SQLite database into NetworkX.
        
        Returns:
            NetworkX directed graph
        """
        self.graph.clear()
        
        cursor = self.conn.cursor()
        
        # Load entities
        cursor.execute("SELECT entity_name, entity_type, mention_count FROM entities")
        entities = cursor.fetchall()
        
        for entity in entities:
            self.graph.add_node(
                entity['entity_name'],
                type=entity['entity_type'],
                mention_count=entity['mention_count']
            )
        
        logger.info(f"Loaded {len(entities)} entities into graph")
        
        # Load relationships
        cursor.execute("""
            SELECT entity1, entity2, relationship_type,
                   source_article_ids, publication_dates, frequency
            FROM relationships
        """)
        relationships = cursor.fetchall()
        
        for rel in relationships:
            self.graph.add_edge(
                rel['entity1'],
                rel['entity2'],
                relationship_type=rel['relationship_type'],
                source_article_ids=json.loads(rel['source_article_ids']),
                publication_dates=json.loads(rel['publication_dates']),
                frequency=rel['frequency']
            )
        
        logger.info(f"Loaded {len(relationships)} relationships into graph")
        
        return self.graph
    
    def get_graph(self) -> nx.DiGraph:
        """Get the current NetworkX graph.
        
        Returns:
            NetworkX directed graph
        """
        if self.graph.number_of_nodes() == 0:
            self.load_graph_from_db()
        return self.graph
    
    def rebuild_from_extractions(self, extractions_data: List[Dict[str, Any]]) -> None:
        """Rebuild graph from scratch using extraction data.
        
        Args:
            extractions_data: List of extraction results from Module 3
        """
        logger.info("Starting graph rebuild from extractions...")
        
        # Clear existing data
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM relationships")
        cursor.execute("DELETE FROM entities")
        self.conn.commit()
        self.graph.clear()
        
        total_relationships = 0
        processed_articles = 0
        
        try:
            for article_data in extractions_data:
                article_id = article_data.get('article_id', '')
                publication_date = article_data.get('publication_date', datetime.utcnow().isoformat())
                relationships = article_data.get('relationships', [])
                
                if not relationships:
                    continue
                
                processed_articles += 1
                
                for rel in relationships:
                    entity1 = rel.get('entity1', '').strip()
                    entity2 = rel.get('entity2', '').strip()
                    relationship_type = rel.get('relationship', '').strip().lower()
                    entity1_type = rel.get('entity1_type', 'Company').strip()
                    entity2_type = rel.get('entity2_type', 'Company').strip()
                    
                    # Skip invalid relationships
                    if not entity1 or not entity2 or not relationship_type:
                        continue
                    
                    if entity1 == entity2:  # Skip self-loops
                        continue
                    
                    # Add relationship (this will ensure entities exist)
                    self.add_or_update_relationship(
                        entity1, entity2, relationship_type,
                        article_id, publication_date,
                        entity1_type, entity2_type
                    )
                    
                    total_relationships += 1
                    
                    # Print progress every 20 relationships
                    if total_relationships % 20 == 0:
                        logger.info(f"Processed {total_relationships} relationships...")
            
            logger.info(
                f"Graph rebuild complete: {processed_articles} articles, "
                f"{total_relationships} relationships, {self.graph.number_of_nodes()} entities"
            )
        
        except Exception as e:
            logger.error(f"Error during graph rebuild: {e}", exc_info=True)
            self.conn.rollback()
            raise
    
    def get_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive details about an entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Dictionary with entity details and relationships, or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get entity metadata
        cursor.execute("SELECT * FROM entities WHERE entity_name = ?", (entity_name,))
        entity_row = cursor.fetchone()
        
        if not entity_row:
            return None
        
        # Get outgoing relationships (entity1 = this entity)
        cursor.execute("""
            SELECT entity2, relationship_type, source_article_ids, 
                   publication_dates, frequency
            FROM relationships
            WHERE entity1 = ?
            ORDER BY frequency DESC
        """, (entity_name,))
        
        outgoing = []
        for rel in cursor.fetchall():
            outgoing.append({
                'target_entity': rel['entity2'],
                'relationship_type': rel['relationship_type'],
                'source_article_ids': json.loads(rel['source_article_ids']),
                'publication_dates': json.loads(rel['publication_dates']),
                'frequency': rel['frequency']
            })
        
        # Get incoming relationships (entity2 = this entity)
        cursor.execute("""
            SELECT entity1, relationship_type, source_article_ids,
                   publication_dates, frequency
            FROM relationships
            WHERE entity2 = ?
            ORDER BY frequency DESC
        """, (entity_name,))
        
        incoming = []
        for rel in cursor.fetchall():
            incoming.append({
                'source_entity': rel['entity1'],
                'relationship_type': rel['relationship_type'],
                'source_article_ids': json.loads(rel['source_article_ids']),
                'publication_dates': json.loads(rel['publication_dates']),
                'frequency': rel['frequency']
            })
        
        return {
            'entity_name': entity_row['entity_name'],
            'entity_type': entity_row['entity_type'],
            'mention_count': entity_row['mention_count'],
            'first_seen': entity_row['first_seen'],
            'last_updated': entity_row['last_updated'],
            'outgoing_relationships': outgoing,
            'incoming_relationships': incoming
        }
    
    def get_relationship_trends(
        self,
        relationship_type: str,
        start_date: str,
        end_date: str
    ) -> List[Tuple[str, int]]:
        """Get time series data for a relationship type.
        
        Args:
            relationship_type: Type of relationship to analyze
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            List of (date, count) tuples
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT publication_dates
            FROM relationships
            WHERE relationship_type = ?
        """, (relationship_type.lower(),))
        
        date_counts: Dict[str, int] = {}
        
        for row in cursor.fetchall():
            dates = json.loads(row['publication_dates'])
            for date in dates:
                if start_date <= date <= end_date:
                    date_counts[date] = date_counts.get(date, 0) + 1
        
        # Sort by date
        sorted_dates = sorted(date_counts.items())
        return sorted_dates
    
    def export_graph_statistics(self) -> Dict[str, Any]:
        """Export comprehensive graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        cursor = self.conn.cursor()
        
        # Total entities
        cursor.execute("SELECT COUNT(*) as count FROM entities")
        total_entities = cursor.fetchone()['count']
        
        # Total relationships
        cursor.execute("SELECT COUNT(*) as count FROM relationships")
        total_relationships = cursor.fetchone()['count']
        
        # Entities by type
        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        entities_by_type = {row['entity_type']: row['count'] for row in cursor.fetchall()}
        
        # Relationships by type
        cursor.execute("""
            SELECT relationship_type, COUNT(*) as count
            FROM relationships
            GROUP BY relationship_type
            ORDER BY count DESC
        """)
        relationships_by_type = {
            row['relationship_type']: row['count'] for row in cursor.fetchall()
        }
        
        # Most connected entities (by degree)
        graph = self.get_graph()
        degrees = dict(graph.degree())
        sorted_degrees = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        most_connected = [
            {'entity': entity, 'degree': degree}
            for entity, degree in sorted_degrees[:10]
        ]
        
        # Date range
        cursor.execute("""
            SELECT publication_dates
            FROM relationships
        """)
        all_dates = []
        for row in cursor.fetchall():
            dates = json.loads(row['publication_dates'])
            all_dates.extend(dates)
        
        date_range = {
            'earliest': min(all_dates) if all_dates else None,
            'latest': max(all_dates) if all_dates else None
        }
        
        return {
            'total_entities': total_entities,
            'total_relationships': total_relationships,
            'entities_by_type': entities_by_type,
            'relationships_by_type': relationships_by_type,
            'most_connected_entities': most_connected,
            'date_range': date_range
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()

