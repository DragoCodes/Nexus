"""Graph builder to orchestrate graph construction from extraction results."""
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.utils.logger import setup_logger
from src.module4_graph.graph_manager import GraphManager

logger = setup_logger(__name__)


class GraphBuilder:
    """Orchestrate graph building from extraction results."""
    
    def __init__(self, graph_manager: GraphManager):
        """Initialize GraphBuilder.
        
        Args:
            graph_manager: GraphManager instance
        """
        self.graph_manager = graph_manager
        logger.info("Initialized GraphBuilder")
    
    def build_from_extraction_file(self, extraction_file_path: str) -> Dict[str, Any]:
        """Build graph from extraction JSON file.
        
        Args:
            extraction_file_path: Path to JSON file with extraction results
            
        Returns:
            Dictionary with build statistics
        """
        import time
        start_time = time.time()
        
        logger.info(f"Loading extraction file: {extraction_file_path}")
        
        # Load extraction file
        file_path = Path(extraction_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Extraction file not found: {extraction_file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            extractions_data = json.load(f)
        
        if not isinstance(extractions_data, list):
            raise ValueError("Extraction file must contain a JSON array")
        
        logger.info(f"Loaded {len(extractions_data)} articles from extraction file")
        
        # Count relationships before rebuild
        total_relationships_found = sum(
            len(article.get('relationships', []))
            for article in extractions_data
        )
        
        # Rebuild graph
        self.graph_manager.rebuild_from_extractions(extractions_data)
        
        # Get statistics
        graph = self.graph_manager.get_graph()
        stats = self.graph_manager.export_graph_statistics()
        
        elapsed_time = time.time() - start_time
        
        build_stats = {
            'total_articles_processed': len(extractions_data),
            'total_relationships_found': total_relationships_found,
            'total_unique_entities': stats['total_entities'],
            'total_unique_relationships': stats['total_relationships'],
            'time_taken_seconds': round(elapsed_time, 2)
        }
        
        logger.info(
            f"Graph build complete: {build_stats['total_articles_processed']} articles, "
            f"{build_stats['total_unique_entities']} entities, "
            f"{build_stats['total_unique_relationships']} relationships, "
            f"took {build_stats['time_taken_seconds']}s"
        )
        
        return build_stats
    
    def incremental_update(self, new_extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Incrementally update graph with new extractions.
        
        Args:
            new_extractions: List of new extraction results
            
        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Incremental update: processing {len(new_extractions)} new articles")
        
        added_entities = set()
        added_relationships = 0
        
        for article_data in new_extractions:
            article_id = article_data.get('article_id', '')
            publication_date = article_data.get('publication_date', '')
            relationships = article_data.get('relationships', [])
            
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
                self.graph_manager.add_or_update_relationship(
                    entity1, entity2, relationship_type,
                    article_id, publication_date,
                    entity1_type, entity2_type
                )
                added_entities.add(entity1)
                added_entities.add(entity2)
                added_relationships += 1
        
        update_stats = {
            'articles_processed': len(new_extractions),
            'new_entities_added': len(added_entities),
            'relationships_added': added_relationships
        }
        
        logger.info(
            f"Incremental update complete: {update_stats['articles_processed']} articles, "
            f"{update_stats['new_entities_added']} entities, "
            f"{update_stats['relationships_added']} relationships"
        )
        
        return update_stats
    
    def validate_graph(self) -> Dict[str, Any]:
        """Validate graph integrity.
        
        Returns:
            Dictionary with validation report
        """
        logger.info("Validating graph integrity...")
        
        issues = []
        fixes_applied = []
        
        graph = self.graph_manager.get_graph()
        
        # Check 1: All edges connect existing nodes
        # This should be automatically handled by NetworkX, but let's verify
        for u, v in graph.edges():
            if u not in graph.nodes() or v not in graph.nodes():
                issues.append(f"Edge ({u}, {v}) connects non-existent nodes")
        
        # Check 2: No self-loops
        self_loops = [(u, v) for u, v in graph.edges() if u == v]
        if self_loops:
            issues.append(f"Found {len(self_loops)} self-loops")
            # Fix: Remove self-loops
            for u, v in self_loops:
                graph.remove_edge(u, v)
                fixes_applied.append(f"Removed self-loop: ({u}, {v})")
        
        # Check 3: All required attributes present
        for node in graph.nodes():
            if 'type' not in graph.nodes[node]:
                issues.append(f"Node {node} missing 'type' attribute")
                # Fix: Set default type
                graph.nodes[node]['type'] = 'Unknown'
                fixes_applied.append(f"Added default type to node {node}")
        
        for u, v in graph.edges():
            if 'relationship_type' not in graph[u][v]:
                issues.append(f"Edge ({u}, {v}) missing 'relationship_type' attribute")
        
        # Check 4: No duplicate relationships (same entity1, entity2, relationship_type)
        # This is handled by the database, but we can verify
        seen_relationships = set()
        duplicates = []
        for u, v, data in graph.edges(data=True):
            rel_type = data.get('relationship_type', '')
            key = (u, v, rel_type)
            if key in seen_relationships:
                duplicates.append(f"Duplicate relationship: {u} --[{rel_type}]--> {v}")
            seen_relationships.add(key)
        
        if duplicates:
            issues.append(f"Found {len(duplicates)} duplicate relationships")
        
        # Get graph statistics
        stats = self.graph_manager.export_graph_statistics()
        
        validation_report = {
            'is_valid': len(issues) == 0,
            'issues_found': len(issues),
            'issues': issues,
            'fixes_applied': fixes_applied,
            'graph_statistics': stats,
            'validation_passed': len(issues) == 0
        }
        
        if validation_report['is_valid']:
            logger.info("Graph validation passed")
        else:
            logger.warning(f"Graph validation found {len(issues)} issues")
        
        return validation_report

