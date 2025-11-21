"""Graph analytics for computing PageRank, communities, and centrality measures."""
import logging
from typing import Dict, List, Optional, Any
import networkx as nx
from networkx import community

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GraphAnalytics:
    """Compute analytics on the knowledge graph."""
    
    def __init__(self, graph: nx.DiGraph):
        """Initialize GraphAnalytics.
        
        Args:
            graph: NetworkX directed graph
        """
        self.graph = graph
        logger.info(f"Initialized GraphAnalytics with graph of {graph.number_of_nodes()} nodes")
    
    def compute_pagerank(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Compute PageRank scores for entities.
        
        Args:
            top_n: Number of top entities to return
            
        Returns:
            List of dictionaries with entity name, score, and type
        """
        if self.graph.number_of_nodes() == 0:
            logger.warning("Graph is empty, cannot compute PageRank")
            return []
        
        try:
            pagerank_scores = nx.pagerank(self.graph)
            
            # Sort by score descending
            sorted_scores = sorted(
                pagerank_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Get entity types from graph
            results = []
            for entity_name, score in sorted_scores[:top_n]:
                entity_type = self.graph.nodes[entity_name].get('type', 'Unknown')
                results.append({
                    'entity_name': entity_name,
                    'score': round(score, 6),
                    'entity_type': entity_type
                })
            
            logger.info(f"Computed PageRank for {len(pagerank_scores)} entities")
            return results
        
        except Exception as e:
            logger.error(f"Error computing PageRank: {e}", exc_info=True)
            return []
    
    def detect_communities(self) -> List[Dict[str, Any]]:
        """Detect communities in the graph using Louvain algorithm.
        
        Returns:
            List of community dictionaries
        """
        if self.graph.number_of_nodes() == 0:
            logger.warning("Graph is empty, cannot detect communities")
            return []
        
        try:
            # Convert to undirected for community detection
            undirected_graph = self.graph.to_undirected()
            
            # Detect communities
            communities = community.louvain_communities(undirected_graph)
            
            results = []
            for idx, community_set in enumerate(communities):
                if len(community_set) == 0:
                    continue
                
                # Get entity types in this community
                entity_types = []
                for entity in community_set:
                    entity_type = self.graph.nodes[entity].get('type', 'Unknown')
                    entity_types.append(entity_type)
                
                # Generate description based on most common entity type
                if entity_types:
                    most_common_type = max(set(entity_types), key=entity_types.count)
                    description = f"{most_common_type} Community"
                else:
                    description = "Community"
                
                results.append({
                    'community_id': idx,
                    'entities': list(community_set),
                    'size': len(community_set),
                    'description': description
                })
            
            logger.info(f"Detected {len(results)} communities")
            return results
        
        except Exception as e:
            logger.error(f"Error detecting communities: {e}", exc_info=True)
            return []
    
    def get_entity_centrality(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """Calculate multiple centrality measures for a specific entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Dictionary with centrality measures and explanations, or None if entity not found
        """
        if entity_name not in self.graph:
            logger.warning(f"Entity {entity_name} not found in graph")
            return None
        
        try:
            # Degree centrality (in-degree and out-degree)
            in_degree = self.graph.in_degree(entity_name)
            out_degree = self.graph.out_degree(entity_name)
            total_degree = in_degree + out_degree
            
            # Degree centrality (normalized)
            degree_centrality = nx.degree_centrality(self.graph).get(entity_name, 0)
            
            # Betweenness centrality
            betweenness = nx.betweenness_centrality(self.graph).get(entity_name, 0)
            
            # Closeness centrality (only for connected graphs)
            try:
                closeness = nx.closeness_centrality(self.graph).get(entity_name, 0)
            except:
                closeness = 0
            
            return {
                'entity_name': entity_name,
                'in_degree': in_degree,
                'out_degree': out_degree,
                'total_degree': total_degree,
                'degree_centrality': round(degree_centrality, 6),
                'betweenness_centrality': round(betweenness, 6),
                'closeness_centrality': round(closeness, 6),
                'explanations': {
                    'in_degree': 'Number of incoming relationships',
                    'out_degree': 'Number of outgoing relationships',
                    'degree_centrality': 'Normalized degree (0-1), higher means more connected',
                    'betweenness_centrality': 'Measures how often entity lies on shortest paths (0-1)',
                    'closeness_centrality': 'Measures average distance to all other entities (0-1)'
                }
            }
        
        except Exception as e:
            logger.error(f"Error computing centrality for {entity_name}: {e}", exc_info=True)
            return None
    
    def get_ego_network(self, entity_name: str, radius: int = 1) -> Optional[nx.DiGraph]:
        """Extract ego network centered on an entity.
        
        Args:
            entity_name: Name of the entity
            radius: Radius of the ego network
            
        Returns:
            Subgraph representing the ego network, or None if entity not found
        """
        if entity_name not in self.graph:
            logger.warning(f"Entity {entity_name} not found in graph")
            return None
        
        try:
            ego_graph = nx.ego_graph(self.graph, entity_name, radius=radius)
            logger.info(f"Extracted ego network for {entity_name} with {ego_graph.number_of_nodes()} nodes")
            return ego_graph
        
        except Exception as e:
            logger.error(f"Error extracting ego network for {entity_name}: {e}", exc_info=True)
            return None
    
    def find_shortest_path(
        self,
        entity1: str,
        entity2: str
    ) -> Optional[Dict[str, Any]]:
        """Find shortest path between two entities.
        
        Args:
            entity1: Source entity
            entity2: Target entity
            
        Returns:
            Dictionary with path and relationship types, or None if no path exists
        """
        if entity1 not in self.graph or entity2 not in self.graph:
            logger.warning(f"One or both entities not found: {entity1}, {entity2}")
            return None
        
        try:
            if not nx.has_path(self.graph, entity1, entity2):
                return None
            
            path = nx.shortest_path(self.graph, entity1, entity2)
            
            # Get relationship types along the path
            relationship_types = []
            for i in range(len(path) - 1):
                edge_data = self.graph[path[i]][path[i + 1]]
                rel_type = edge_data.get('relationship_type', 'unknown')
                relationship_types.append(rel_type)
            
            return {
                'path': path,
                'length': len(path) - 1,
                'relationship_types': relationship_types
            }
        
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.error(f"Error finding shortest path: {e}", exc_info=True)
            return None
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """Calculate overall graph statistics.
        
        Returns:
            Dictionary with network statistics and explanations
        """
        if self.graph.number_of_nodes() == 0:
            return {
                'nodes': 0,
                'edges': 0,
                'message': 'Graph is empty'
            }
        
        try:
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
            
            # Average degree
            degrees = dict(self.graph.degree())
            avg_degree = sum(degrees.values()) / num_nodes if num_nodes > 0 else 0
            
            # Network density
            density = nx.density(self.graph)
            
            # Connected components (for undirected version)
            undirected = self.graph.to_undirected()
            num_components = nx.number_connected_components(undirected)
            
            # Average clustering coefficient
            try:
                clustering = nx.average_clustering(undirected)
            except:
                clustering = 0
            
            # Diameter (if graph is connected)
            diameter = None
            if num_components == 1:
                try:
                    diameter = nx.diameter(undirected)
                except:
                    pass
            
            return {
                'nodes': num_nodes,
                'edges': num_edges,
                'average_degree': round(avg_degree, 2),
                'density': round(density, 6),
                'connected_components': num_components,
                'average_clustering': round(clustering, 6),
                'diameter': diameter,
                'explanations': {
                    'nodes': 'Total number of entities',
                    'edges': 'Total number of relationships',
                    'average_degree': 'Average number of connections per entity',
                    'density': 'Ratio of actual edges to possible edges (0-1)',
                    'connected_components': 'Number of disconnected subgraphs',
                    'average_clustering': 'Measure of how nodes cluster together (0-1)',
                    'diameter': 'Longest shortest path in the graph (if connected)'
                }
            }
        
        except Exception as e:
            logger.error(f"Error computing network statistics: {e}", exc_info=True)
            return {'error': str(e)}

