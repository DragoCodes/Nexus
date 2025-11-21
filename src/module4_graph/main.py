"""Main script to build the knowledge graph from extraction results."""
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional  # Add this line
import argparse

from src.utils.logger import setup_logger
from src.module4_graph.graph_manager import GraphManager
from src.module4_graph.graph_builder import GraphBuilder
from src.module4_graph.graph_analytics import GraphAnalytics

logger = setup_logger(__name__)


def create_backup(db_path: str) -> Optional[str]:
    """Create backup of SQLite database before rebuild.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Path to backup file, or None if backup failed
    """
    db_file = Path(db_path)
    if not db_file.exists():
        logger.info("No existing database to backup")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None


def ensure_exports_directory():
    """Ensure data/exports directory exists."""
    exports_dir = Path("data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured exports directory exists: {exports_dir}")


def main():
    """Main function to build knowledge graph."""
    parser = argparse.ArgumentParser(description="Build knowledge graph from extraction results")
    parser.add_argument(
        "--extraction-file",
        type=str,
        default="data/exports/extractions.json",
        help="Path to extraction results JSON file"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/nexus_graph.db",
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup of existing database"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Knowledge Graph Builder - Module 4")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Ensure exports directory exists
    ensure_exports_directory()
    
    # Create backup if database exists
    if not args.skip_backup:
        backup_path = create_backup(args.db_path)
    
    # Initialize components
    logger.info("Initializing GraphManager...")
    graph_manager = GraphManager(db_path=args.db_path)
    
    logger.info("Initializing GraphBuilder...")
    graph_builder = GraphBuilder(graph_manager)
    
    # Build graph from extraction file
    logger.info(f"Building graph from: {args.extraction_file}")
    try:
        build_stats = graph_builder.build_from_extraction_file(args.extraction_file)
        logger.info(f"Build statistics: {build_stats}")
    except FileNotFoundError as e:
        logger.error(f"Extraction file not found: {e}")
        logger.error("Please run Module 3 first to generate extraction results")
        return
    except Exception as e:
        logger.error(f"Error building graph: {e}", exc_info=True)
        return
    
    # Validate graph
    logger.info("Validating graph...")
    validation_report = graph_builder.validate_graph()
    
    if not validation_report['is_valid']:
        logger.warning(f"Validation found {validation_report['issues_found']} issues:")
        for issue in validation_report['issues']:
            logger.warning(f"  - {issue}")
        if validation_report['fixes_applied']:
            logger.info("Applied fixes:")
            for fix in validation_report['fixes_applied']:
                logger.info(f"  - {fix}")
    else:
        logger.info("Graph validation passed!")
    
    # Initialize analytics
    logger.info("Initializing GraphAnalytics...")
    graph = graph_manager.get_graph()
    analytics = GraphAnalytics(graph)
    
    # Compute PageRank
    logger.info("Computing PageRank...")
    pagerank_results = analytics.compute_pagerank(top_n=20)
    
    # Save PageRank results
    pagerank_file = Path("data/exports/pagerank_results.json")
    with open(pagerank_file, 'w', encoding='utf-8') as f:
        json.dump(pagerank_results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved PageRank results to: {pagerank_file}")
    
    # Detect communities
    logger.info("Detecting communities...")
    communities = analytics.detect_communities()
    
    # Save community results
    communities_file = Path("data/exports/communities.json")
    with open(communities_file, 'w', encoding='utf-8') as f:
        json.dump(communities, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved community results to: {communities_file}")
    
    # Compute network statistics
    logger.info("Computing network statistics...")
    network_stats = analytics.get_network_statistics()
    
    # Save network statistics
    stats_file = Path("data/exports/network_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(network_stats, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved network statistics to: {stats_file}")
    
    # Get graph statistics
    graph_stats = graph_manager.export_graph_statistics()
    
    # Generate build report
    elapsed_time = time.time() - start_time
    report_lines = [
        "=" * 60,
        "KNOWLEDGE GRAPH BUILD REPORT",
        "=" * 60,
        f"Build Date: {datetime.now().isoformat()}",
        f"Total Build Time: {elapsed_time:.2f} seconds",
        "",
        "BUILD STATISTICS:",
        f"  Articles Processed: {build_stats['total_articles_processed']}",
        f"  Relationships Found: {build_stats['total_relationships_found']}",
        f"  Unique Entities: {build_stats['total_unique_entities']}",
        f"  Unique Relationships: {build_stats['total_unique_relationships']}",
        "",
        "GRAPH STATISTICS:",
        f"  Total Entities: {graph_stats['total_entities']}",
        f"  Total Relationships: {graph_stats['total_relationships']}",
        "",
        "ENTITIES BY TYPE:",
    ]
    
    for entity_type, count in graph_stats['entities_by_type'].items():
        report_lines.append(f"  {entity_type}: {count}")
    
    report_lines.extend([
        "",
        "RELATIONSHIPS BY TYPE:",
    ])
    
    for rel_type, count in list(graph_stats['relationships_by_type'].items())[:10]:
        report_lines.append(f"  {rel_type}: {count}")
    
    report_lines.extend([
        "",
        "MOST CONNECTED ENTITIES (Top 10):",
    ])
    
    for entity_info in graph_stats['most_connected_entities'][:10]:
        report_lines.append(f"  {entity_info['entity']}: {entity_info['degree']} connections")
    
    report_lines.extend([
        "",
        "NETWORK STATISTICS:",
        f"  Nodes: {network_stats.get('nodes', 0)}",
        f"  Edges: {network_stats.get('edges', 0)}",
        f"  Average Degree: {network_stats.get('average_degree', 0)}",
        f"  Density: {network_stats.get('density', 0)}",
        f"  Connected Components: {network_stats.get('connected_components', 0)}",
        f"  Average Clustering: {network_stats.get('average_clustering', 0)}",
    ])
    
    if network_stats.get('diameter'):
        report_lines.append(f"  Diameter: {network_stats['diameter']}")
    
    report_lines.extend([
        "",
        "PAGERANK TOP 10:",
    ])
    
    for entity_info in pagerank_results[:10]:
        report_lines.append(
            f"  {entity_info['entity_name']} ({entity_info['entity_type']}): "
            f"{entity_info['score']:.6f}"
        )
    
    report_lines.extend([
        "",
        f"COMMUNITIES DETECTED: {len(communities)}",
    ])
    
    for community_info in communities[:5]:
        report_lines.append(
            f"  Community {community_info['community_id']}: "
            f"{community_info['description']} ({community_info['size']} entities)"
        )
    
    report_lines.extend([
        "",
        "VALIDATION:",
        f"  Status: {'PASSED' if validation_report['is_valid'] else 'ISSUES FOUND'}",
        f"  Issues Found: {validation_report['issues_found']}",
    ])
    
    if validation_report['fixes_applied']:
        report_lines.append(f"  Fixes Applied: {len(validation_report['fixes_applied'])}")
    
    report_lines.append("=" * 60)
    
    # Save build report
    report_file = Path("data/exports/build_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # Print summary
    print('\n'.join(report_lines))
    logger.info(f"Saved build report to: {report_file}")
    
    # Close database connection
    graph_manager.close()
    
    logger.info("=" * 60)
    logger.info("Knowledge graph build complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

