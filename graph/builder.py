"""
Knowledge Graph Builder
Constructs and manages NetworkX graph from extraction triples
"""
import networkx as nx
from typing import List, Dict, Optional
import json
from datetime import datetime
from pathlib import Path


class KnowledgeGraphBuilder:
    def __init__(self):
        """Initialize empty directed multigraph"""
        self.graph = nx.MultiDiGraph()
        self.entity_index = {}  # Fast entity lookup
        self.relationship_stats = {}  # Track relationship frequencies
    
    def add_triple(
        self,
        entity1: str,
        entity1_type: str,
        relationship: str,
        entity2: str,
        entity2_type: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a relationship triple to the graph (upsert logic)
        
        Args:
            entity1: Source entity name
            entity1_type: Source entity type
            relationship: Relationship type
            entity2: Target entity name
            entity2_type: Target entity type
            metadata: Edge metadata (article_id, publication_date, etc.)
        """
        # Normalize entity names
        entity1 = entity1.strip()
        entity2 = entity2.strip()
        
        # Add or update nodes
        if not self.graph.has_node(entity1):
            self.graph.add_node(
                entity1,
                type=entity1_type,
                label=entity1,
                degree=0
            )
            self.entity_index[entity1.lower()] = entity1
        
        if not self.graph.has_node(entity2):
            self.graph.add_node(
                entity2,
                type=entity2_type,
                label=entity2,
                degree=0
            )
            self.entity_index[entity2.lower()] = entity2
        
        # Prepare edge data
        edge_data = {
            'relationship': relationship,
            'created_at': datetime.now().isoformat()
        }
        
        if metadata:
            edge_data.update(metadata)
        
        # Add edge (multigraph allows multiple edges between same nodes)
        self.graph.add_edge(entity1, entity2, **edge_data)
        
        # Update relationship statistics
        if relationship not in self.relationship_stats:
            self.relationship_stats[relationship] = 0
        self.relationship_stats[relationship] += 1
        
        # Update node degrees
        self.graph.nodes[entity1]['degree'] = self.graph.degree(entity1)
        self.graph.nodes[entity2]['degree'] = self.graph.degree(entity2)
    
    def add_extraction_result(self, extraction: Dict):
        """
        Add all triples from an extraction result
        
        Args:
            extraction: Extraction result dict with 'triples' list
        """
        article_id = extraction.get('article_id')
        metadata_base = extraction.get('metadata', {})
        
        for triple in extraction.get('triples', []):
            metadata = {
                'article_id': article_id,
                'source': metadata_base.get('source'),
                'publication_date': metadata_base.get('publication_date'),
                'confidence': triple.get('confidence', 1.0)
            }
            
            self.add_triple(
                entity1=triple['entity1'],
                entity1_type=triple['entity1_type'],
                relationship=triple['relationship'],
                entity2=triple['entity2'],
                entity2_type=triple['entity2_type'],
                metadata=metadata
            )
    
    def load_from_cache(self, cache_dir: str = "data/extractions"):
        """
        Load all cached extractions into graph
        
        Args:
            cache_dir: Directory containing extraction JSON files
        """
        cache_path = Path(cache_dir)
        
        if not cache_path.exists():
            print(f"Cache directory not found: {cache_dir}")
            return 0
        
        count = 0
        for json_file in cache_path.rglob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    extraction = json.load(f)
                
                self.add_extraction_result(extraction)
                count += 1
            
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
        
        print(f"Loaded {count} extractions into graph")
        return count
    
    def load_from_json(self, json_path: str):
        """
        Load extractions from aggregated JSON file
        
        Args:
            json_path: Path to JSON file with list of extractions
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            extractions = json.load(f)
        
        for extraction in extractions:
            self.add_extraction_result(extraction)
        
        print(f"Loaded {len(extractions)} extractions from {json_path}")
        return len(extractions)
    
    def get_entity(self, entity_name: str) -> Optional[Dict]:
        """
        Get entity node data
        
        Args:
            entity_name: Entity name (case-insensitive)
            
        Returns:
            Node data dict or None
        """
        # Try exact match first
        if entity_name in self.graph.nodes:
            return dict(self.graph.nodes[entity_name])
        
        # Try case-insensitive lookup
        entity_key = entity_name.lower()
        if entity_key in self.entity_index:
            canonical_name = self.entity_index[entity_key]
            return dict(self.graph.nodes[canonical_name])
        
        return None
    
    def get_relationships(self, entity_name: str) -> List[Dict]:
        """
        Get all relationships for an entity
        
        Args:
            entity_name: Entity name
            
        Returns:
            List of relationship dicts
        """
        # Normalize entity name
        entity_key = entity_name.lower()
        if entity_key in self.entity_index:
            entity_name = self.entity_index[entity_key]
        
        if entity_name not in self.graph.nodes:
            return []
        
        relationships = []
        
        # Outgoing edges
        for _, target, data in self.graph.out_edges(entity_name, data=True):
            relationships.append({
                'direction': 'outgoing',
                'entity': entity_name,
                'related_entity': target,
                'relationship': data['relationship'],
                'metadata': {
                    k: v for k, v in data.items() 
                    if k != 'relationship'
                }
            })
        
        # Incoming edges
        for source, _, data in self.graph.in_edges(entity_name, data=True):
            relationships.append({
                'direction': 'incoming',
                'entity': entity_name,
                'related_entity': source,
                'relationship': data['relationship'],
                'metadata': {
                    k: v for k, v in data.items() 
                    if k != 'relationship'
                }
            })
        
        return relationships
    
    def get_statistics(self) -> Dict:
        """Get graph statistics"""
        return {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'entity_types': self._count_entity_types(),
            'relationship_types': len(self.relationship_stats),
            'top_relationships': self._get_top_relationships(5),
            'density': nx.density(self.graph),
            'is_connected': nx.is_weakly_connected(self.graph)
        }
    
    def _count_entity_types(self) -> Dict[str, int]:
        """Count nodes by entity type"""
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            entity_type = data.get('type', 'Unknown')
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        return type_counts
    
    def _get_top_relationships(self, k: int = 5) -> List[Dict]:
        """Get most frequent relationships"""
        sorted_rels = sorted(
            self.relationship_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            {'relationship': rel, 'count': count}
            for rel, count in sorted_rels[:k]
        ]
    
    def save_graph(self, filepath: str = "data/knowledge_graph.gexf"):
        """Save graph to file (GEXF format for Gephi compatibility)"""
        nx.write_gexf(self.graph, filepath)
        print(f"Graph saved to {filepath}")
    
    def load_graph(self, filepath: str = "data/knowledge_graph.gexf"):
        """Load graph from file"""
        self.graph = nx.read_gexf(filepath, node_type=str)
        
        # Rebuild entity index
        self.entity_index = {
            name.lower(): name 
            for name in self.graph.nodes()
        }
        
        print(f"Graph loaded from {filepath}")


# Quick test
if __name__ == "__main__":
    import os
    
    builder = KnowledgeGraphBuilder()
    
    # Try to load from cache
    if os.path.exists("data/extractions"):
        builder.load_from_cache()
    elif os.path.exists("mock_data/mock_graph.json"):
        # Create mock graph data if needed
        mock_extractions = [
            {
                'article_id': 'test-1',
                'triples': [
                    {
                        'entity1': 'NVIDIA',
                        'entity1_type': 'Company',
                        'relationship': 'partners_with',
                        'entity2': 'TSMC',
                        'entity2_type': 'Company',
                        'confidence': 1.0
                    }
                ],
                'metadata': {
                    'headline': 'Test Article',
                    'source': 'Test',
                    'publication_date': '2024-11-17'
                }
            }
        ]
        
        for ext in mock_extractions:
            builder.add_extraction_result(ext)
    
    # Display statistics
    print("\nGraph Statistics:")
    stats = builder.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # Test entity lookup
    if builder.graph.number_of_nodes() > 0:
        test_entity = list(builder.graph.nodes())[0]
        print(f"\nRelationships for '{test_entity}':")
        rels = builder.get_relationships(test_entity)
        for rel in rels[:3]:
            print(f"  {rel['direction']}: {rel['relationship']} -> {rel['related_entity']}")