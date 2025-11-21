"""Main application interface for Nexus."""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import (
    ArticleSearchResult,
    EntityDetails,
    PageRankResult,
    Community,
    TrendDataPoint,
    NetworkStatistics
)

# Import dependencies
from module1_ingestion.local_db_handler import LocalDBHandler
from module1_ingestion.config import validate_config as validate_ingestion_config, DB_PATH
from module2_search.search_engine import SearchEngine
from module2_search.indexer import InvertedIndex
from module2_search.preprocessor import TextPreprocessor

# Try to import module4 components (may not exist yet)
try:
    from module4_graph.graph_manager import GraphManager
    from module4_graph.graph_analytics import GraphAnalytics
    MODULE4_AVAILABLE = True
except ImportError:
    MODULE4_AVAILABLE = False
    GraphManager = None
    GraphAnalytics = None

from utils.logger import setup_logger

logger = setup_logger(__name__)


class NexusApp:
    """Main application interface for Nexus Financial Intelligence Knowledge Graph."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(NexusApp, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, 
                 index_path: Optional[str] = None,
                 graph_db_path: Optional[str] = None,
                 db_path: Optional[str] = None):
        """
        Initialize NexusApp with all components.
        
        Args:
            index_path: Path to saved inverted index (default: data/index/inverted_index.pkl)
            graph_db_path: Path to SQLite graph database (default: data/nexus_graph.db)
            db_path: Path to SQLite articles database (optional, uses config if not provided)
        """
        if self._initialized:
            return
        
        logger.info("Initializing NexusApp...")
        
        # Set default paths
        project_root = Path(__file__).parent.parent.parent
        if index_path is None:
            index_path = str(project_root / "data" / "index" / "inverted_index.pkl")
        if graph_db_path is None:
            graph_db_path = str(project_root / "data" / "nexus_graph.db")
        
        # Initialize local database connection
        logger.info("Connecting to local database...")
        try:
            articles_db_path = db_path if db_path else DB_PATH
            self.db_handler = LocalDBHandler(db_path=articles_db_path)
            self.db_handler.connect()
            logger.info("Local database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to local database: {e}")
            raise
        
        # Initialize SearchEngine
        logger.info("Loading search index...")
        try:
            index_file = Path(index_path)
            if not index_file.exists():
                raise FileNotFoundError(f"Index file not found: {index_path}")
            
            # Load index from disk
            preprocessor = TextPreprocessor()
            inverted_index = InvertedIndex(preprocessor)
            inverted_index.load_from_disk(str(index_file))
            
            # Create SearchEngine
            self.search_engine = SearchEngine(
                inverted_index=inverted_index,
                db_handler=self.db_handler,
                preprocessor=preprocessor
            )
            logger.info("SearchEngine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SearchEngine: {e}")
            raise
        
        # Initialize GraphManager and GraphAnalytics (if available)
        self.graph_manager = None
        self.graph_analytics = None
        
        if MODULE4_AVAILABLE:
            try:
                logger.info("Initializing GraphManager...")
                self.graph_manager = GraphManager(graph_db_path)
                self.graph_manager.load_graph_from_db()
                logger.info("GraphManager initialized successfully")
                
                logger.info("Initializing GraphAnalytics...")
                graph = self.graph_manager.get_graph()
                self.graph_analytics = GraphAnalytics(graph)
                logger.info("GraphAnalytics initialized successfully")
            except Exception as e:
                logger.warning(f"Graph components not available: {e}")
                logger.warning("Continuing without graph functionality")
        else:
            logger.warning("Module 4 not available. Graph functionality will be disabled.")
        
        # Initialize caches
        self._pagerank_cache = None
        self._communities_cache = None
        self._network_stats_cache = None
        
        self._initialized = True
        logger.info("NexusApp initialization complete")
    
    def search_articles(self, query: str, k: int = 10) -> List[ArticleSearchResult]:
        """
        Search for articles matching the query.
        
        Args:
            query: Search query string
            k: Number of top results to return (default: 10)
            
        Returns:
            List of ArticleSearchResult objects
        """
        start_time = time.time()
        
        try:
            # Call search engine
            results = self.search_engine.search(query, k=k)
            
            # Convert to ArticleSearchResult objects
            article_results = []
            for result in results:
                # Handle publication_date conversion
                pub_date = result.get('publication_date', '')
                if isinstance(pub_date, str):
                    try:
                        # Try parsing ISO format
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        # If parsing fails, use current date as fallback
                        pub_date = datetime.now()
                elif not isinstance(pub_date, datetime):
                    pub_date = datetime.now()
                
                article_results.append(ArticleSearchResult(
                    article_id=result['article_id'],
                    score=result['score'],
                    headline=result.get('headline', ''),
                    publication_date=pub_date,
                    source=result.get('source', ''),
                    url=result.get('url', '')
                ))
            
            elapsed_time = time.time() - start_time
            logger.info(f"Search completed in {elapsed_time:.3f}s, found {len(article_results)} results")
            
            return article_results
            
        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            return []
    
    def get_entity_details(self, entity_name: str) -> Optional[EntityDetails]:
        """
        Get detailed information about an entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            EntityDetails object or None if entity not found
        """
        if not self.graph_manager:
            logger.warning("GraphManager not available")
            return None
        
        try:
            # Get entity details from GraphManager
            entity_info = self.graph_manager.get_entity_details(entity_name)
            
            if not entity_info:
                return None
            
            # Calculate total degree
            graph = self.graph_manager.get_graph()
            if entity_name in graph:
                total_degree = graph.degree(entity_name)
            else:
                total_degree = len(entity_info.get('incoming_relationships', [])) + \
                              len(entity_info.get('outgoing_relationships', []))
            
            return EntityDetails(
                entity_name=entity_info.get('entity_name', entity_name),
                entity_type=entity_info.get('entity_type', 'Unknown'),
                mention_count=entity_info.get('mention_count', 0),
                incoming_relationships=entity_info.get('incoming_relationships', []),
                outgoing_relationships=entity_info.get('outgoing_relationships', []),
                total_degree=total_degree
            )
            
        except Exception as e:
            logger.error(f"Error getting entity details: {e}", exc_info=True)
            return None
    
    def get_all_entities(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of all entities, optionally filtered by type.
        
        Args:
            entity_type: Optional filter by entity type
            
        Returns:
            List of entity dictionaries sorted by mention_count descending
        """
        if not self.graph_manager:
            logger.warning("GraphManager not available")
            return []
        
        try:
            graph = self.graph_manager.get_graph()
            entities = []
            
            for node_name, node_data in graph.nodes(data=True):
                # Filter by type if specified
                if entity_type and node_data.get('type') != entity_type:
                    continue
                
                entities.append({
                    'entity_name': node_name,
                    'entity_type': node_data.get('type', 'Unknown'),
                    'mention_count': node_data.get('mention_count', 0)
                })
            
            # Sort by mention_count descending
            entities.sort(key=lambda x: x['mention_count'], reverse=True)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error getting all entities: {e}", exc_info=True)
            return []
    
    def compute_pagerank(self) -> List[PageRankResult]:
        """
        Compute PageRank for all entities.
        
        Returns:
            List of PageRankResult objects, sorted by score descending
        """
        if not self.graph_analytics:
            logger.warning("GraphAnalytics not available")
            return []
        
        # Return cached result if available
        if self._pagerank_cache is not None:
            return self._pagerank_cache
        
        try:
            # Compute PageRank
            pagerank_results = self.graph_analytics.compute_pagerank()
            
            # Format as PageRankResult objects
            results = []
            graph = self.graph_manager.get_graph()
            
            # Handle different return formats (dict or list of tuples)
            if isinstance(pagerank_results, dict):
                # Sort by score descending
                sorted_results = sorted(pagerank_results.items(), key=lambda x: x[1], reverse=True)
            else:
                # Assume it's already a list of tuples
                sorted_results = sorted(pagerank_results, key=lambda x: x[1] if isinstance(x, tuple) else x.get('score', 0), reverse=True)
            
            for rank, item in enumerate(sorted_results, start=1):
                if isinstance(item, tuple):
                    entity_name, score = item
                elif isinstance(item, dict):
                    entity_name = item.get('entity_name', '')
                    score = item.get('score', 0.0)
                else:
                    continue
                
                entity_type = 'Unknown'
                if entity_name in graph:
                    entity_type = graph.nodes[entity_name].get('type', 'Unknown')
                
                results.append(PageRankResult(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    score=float(score),
                    rank=rank
                ))
            
            # Cache results
            self._pagerank_cache = results
            
            return results
            
        except Exception as e:
            logger.error(f"Error computing PageRank: {e}", exc_info=True)
            return []
    
    def detect_communities(self) -> List[Community]:
        """
        Detect communities in the knowledge graph.
        
        Returns:
            List of Community objects
        """
        if not self.graph_analytics:
            logger.warning("GraphAnalytics not available")
            return []
        
        # Return cached result if available
        if self._communities_cache is not None:
            return self._communities_cache
        
        try:
            # Detect communities
            communities_data = self.graph_analytics.detect_communities()
            
            # Format as Community objects
            communities = []
            graph = self.graph_manager.get_graph()
            
            # Handle different return formats (list of sets or list of dicts)
            for comm_id, comm_data in enumerate(communities_data):
                # Handle both set and dict formats
                if isinstance(comm_data, set):
                    entities = list(comm_data)
                elif isinstance(comm_data, dict):
                    entities = list(comm_data.get('entities', []))
                else:
                    entities = list(comm_data) if comm_data else []
                
                # Count entity types
                dominant_types = {}
                for entity_name in entities:
                    if entity_name in graph:
                        entity_type = graph.nodes[entity_name].get('type', 'Unknown')
                        dominant_types[entity_type] = dominant_types.get(entity_type, 0) + 1
                
                # Generate description
                if dominant_types:
                    top_type = max(dominant_types.items(), key=lambda x: x[1])
                    description = f"{top_type[0]} Community ({top_type[1]} entities)"
                else:
                    description = "Mixed Community"
                
                communities.append(Community(
                    community_id=comm_id,
                    entities=entities,
                    size=len(entities),
                    dominant_types=dominant_types,
                    description=description
                ))
            
            # Cache results
            self._communities_cache = communities
            
            return communities
            
        except Exception as e:
            logger.error(f"Error detecting communities: {e}", exc_info=True)
            return []
    
    def get_relationship_trends(self, 
                                relationship_type: str,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[TrendDataPoint]:
        """
        Get trend data for a specific relationship type.
        
        Args:
            relationship_type: Type of relationship to analyze
            start_date: Optional start date (ISO format string)
            end_date: Optional end date (ISO format string)
            
        Returns:
            List of TrendDataPoint objects
        """
        if not self.graph_manager:
            logger.warning("GraphManager not available")
            return []
        
        try:
            # Provide default dates if not specified
            if start_date is None:
                from datetime import datetime, timedelta
                start_date = (datetime.now() - timedelta(days=30)).isoformat()
            if end_date is None:
                from datetime import datetime
                end_date = datetime.now().isoformat()
            
            # Get trend data from GraphManager
            trend_data = self.graph_manager.get_relationship_trends(
                relationship_type=relationship_type,
                start_date=start_date,
                end_date=end_date
            )
            
            # Format as TrendDataPoint objects
            trend_points = []
            for date, count in trend_data:
                trend_points.append(TrendDataPoint(
                    date=str(date),
                    count=count,
                    relationship_type=relationship_type
                ))
            
            return trend_points
            
        except Exception as e:
            logger.error(f"Error getting relationship trends: {e}", exc_info=True)
            return []
    
    def get_network_statistics(self) -> NetworkStatistics:
        """
        Get overall network statistics.
        
        Returns:
            NetworkStatistics object
        """
        if not self.graph_analytics:
            logger.warning("GraphAnalytics not available")
            return NetworkStatistics(
                total_entities=0,
                total_relationships=0,
                average_degree=0.0,
                density=0.0,
                description="Graph analytics not available"
            )
        
        # Return cached result if available
        if self._network_stats_cache is not None:
            return self._network_stats_cache
        
        try:
            # Get statistics from GraphAnalytics
            stats = self.graph_analytics.get_network_statistics()
            
            # Format as NetworkStatistics object
            network_stats = NetworkStatistics(
                total_entities=stats.get('total_entities', 0),
                total_relationships=stats.get('total_relationships', 0),
                average_degree=stats.get('average_degree', 0.0),
                density=stats.get('density', 0.0),
                description=stats.get('description', 'Network statistics')
            )
            
            # Cache results
            self._network_stats_cache = network_stats
            
            return network_stats
            
        except Exception as e:
            logger.error(f"Error getting network statistics: {e}", exc_info=True)
            return NetworkStatistics(
                total_entities=0,
                total_relationships=0,
                average_degree=0.0,
                density=0.0,
                description=f"Error: {str(e)}"
            )
    
    def get_graph_for_visualization(self, 
                                    filter_type: Optional[str] = None,
                                    min_connections: int = 1):
        """
        Get NetworkX graph for visualization with optional filters.
        
        Args:
            filter_type: Optional filter by entity type
            min_connections: Minimum number of connections (degree) for nodes to include
            
        Returns:
            Filtered NetworkX graph object
        """
        if not self.graph_manager:
            logger.warning("GraphManager not available")
            return None
        
        try:
            import networkx as nx
            
            # Get full graph
            graph = self.graph_manager.get_graph()
            
            # Create a copy to filter
            filtered_graph = graph.copy()
            
            # Apply filters
            if filter_type:
                # Remove nodes that don't match the type
                nodes_to_remove = [
                    node for node, data in filtered_graph.nodes(data=True)
                    if data.get('type') != filter_type
                ]
                filtered_graph.remove_nodes_from(nodes_to_remove)
            
            if min_connections > 0:
                # Remove nodes with degree less than min_connections
                nodes_to_remove = [
                    node for node in filtered_graph.nodes()
                    if filtered_graph.degree(node) < min_connections
                ]
                filtered_graph.remove_nodes_from(nodes_to_remove)
            
            return filtered_graph
            
        except Exception as e:
            logger.error(f"Error getting graph for visualization: {e}", exc_info=True)
            return None
    
    def rebuild_graph(self) -> Dict[str, Any]:
        """
        Rebuild the graph from scratch by re-running extraction on all articles.
        
        Returns:
            Dictionary with success status and message
        """
        if not self.graph_manager:
            return {
                'success': False,
                'message': 'GraphManager not available'
            }
        
        try:
            logger.info("Starting graph rebuild...")
            
            # TODO: This would need to integrate with Module 3 extraction service
            # For now, we'll just clear caches and reload the graph
            # In a full implementation, this would:
            # 1. Get all articles from MongoDB
            # 2. Run extraction on each article
            # 3. Rebuild graph from extraction results
            
            # Clear caches
            self._pagerank_cache = None
            self._communities_cache = None
            self._network_stats_cache = None
            
            # Reload graph from database
            self.graph_manager.load_graph_from_db()
            
            # Reinitialize GraphAnalytics with new graph
            if self.graph_analytics:
                graph = self.graph_manager.get_graph()
                self.graph_analytics = GraphAnalytics(graph)
            
            logger.info("Graph rebuild complete")
            
            return {
                'success': True,
                'message': 'Graph rebuilt successfully'
            }
            
        except Exception as e:
            logger.error(f"Error rebuilding graph: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error rebuilding graph: {str(e)}'
            }
    
    def invalidate_caches(self):
        """Invalidate all cached results."""
        self._pagerank_cache = None
        self._communities_cache = None
        self._network_stats_cache = None
        logger.info("All caches invalidated")

