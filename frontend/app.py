"""Main Streamlit application for Nexus Financial Intelligence Knowledge Graph."""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.module5_api.app import NexusApp

# Page configuration
st.set_page_config(
    page_title="Nexus - Financial Intelligence Knowledge Graph",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_app():
    """Initialize NexusApp singleton."""
    try:
        app = NexusApp()
        return app
    except Exception as e:
        st.error(f"Failed to initialize application: {e}")
        st.info("Please ensure:")
        st.info("1. MongoDB is running and accessible")
        st.info("2. Index file exists at data/index/inverted_index.pkl")
        st.info("3. Graph database exists at data/nexus_graph.db")
        return None


def main():
    """Main application entry point."""
    
    # Initialize app
    if 'nexus_app' not in st.session_state:
        with st.spinner("Initializing Nexus..."):
            st.session_state.nexus_app = initialize_app()
    
    app = st.session_state.nexus_app
    
    if app is None:
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.title("🕸️ Nexus")
        st.markdown("**Financial Intelligence Knowledge Graph**")
        st.divider()
        
        # Navigation
        st.markdown("### Navigation")
        page = st.radio(
            "Select Page",
            ["Home", "📰 News Search", "🕸️ Knowledge Graph", "📊 Analytics", "📈 Trends"],
            index=0,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Statistics Summary
        st.markdown("### Statistics")
        
        try:
            if app.graph_manager:
                graph = app.graph_manager.get_graph()
                total_entities = graph.number_of_nodes()
                total_relationships = graph.number_of_edges()
                
                st.metric("Total Entities", total_entities)
                st.metric("Total Relationships", total_relationships)
                
                # Get article count
                try:
                    total_articles = app.db_handler.get_article_count()
                    st.metric("Total Articles", total_articles)
                except:
                    st.metric("Total Articles", "N/A")
            else:
                st.info("Graph not available")
        except Exception as e:
            st.warning(f"Could not load statistics: {e}")
        
        st.divider()
        
        # Data refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("Refreshing data..."):
                result = app.rebuild_graph()
                if result.get('success'):
                    st.success("Data refreshed!")
                    st.rerun()
                else:
                    st.error(f"Refresh failed: {result.get('message')}")
        
        st.divider()
        st.markdown("### About")
        st.caption("Nexus extracts and visualizes financial relationships from news articles using AI-powered knowledge graph technology.")
    
    # Main content based on page selection
    if page == "Home":
        show_home_page(app)
    elif page == "📰 News Search":
        # Import and run news search page
        import importlib.util
        news_search_path = Path(__file__).parent / "pages" / "1_📰_News_Search.py"
        spec = importlib.util.spec_from_file_location("news_search", news_search_path)
        news_search_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(news_search_module)
        news_search_module.main()
    elif page == "🕸️ Knowledge Graph":
        # Import and run knowledge graph page
        import importlib.util
        kg_path = Path(__file__).parent / "pages" / "2_🕸️_Knowledge_Graph.py"
        spec = importlib.util.spec_from_file_location("knowledge_graph", kg_path)
        kg_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kg_module)
        kg_module.main()
    elif page == "📊 Analytics":
        # Import and run analytics page
        import importlib.util
        analytics_path = Path(__file__).parent / "pages" / "3_📊_Analytics.py"
        spec = importlib.util.spec_from_file_location("analytics", analytics_path)
        analytics_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analytics_module)
        analytics_module.main()
    elif page == "📈 Trends":
        # Import and run trends page
        import importlib.util
        trends_path = Path(__file__).parent / "pages" / "4_📈_Trends.py"
        spec = importlib.util.spec_from_file_location("trends", trends_path)
        trends_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trends_module)
        trends_module.main()


def show_home_page(app):
    """Display the home/dashboard page."""
    
    # Hero Section
    st.markdown('<div class="main-header">🕸️ Nexus</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Financial Intelligence Knowledge Graph</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **Nexus** is an AI-powered knowledge graph system that extracts and visualizes financial relationships 
    from news articles. Discover connections between companies, people, products, and organizations through 
    an interactive graph interface.
    """)
    
    st.divider()
    
    # Key Value Propositions
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        **🔍 Intelligent Search**
        
        Search financial news articles using BM25 ranking algorithm
        """)
    
    with col2:
        st.markdown("""
        **🕸️ Knowledge Graph**
        
        Interactive visualization of entity relationships
        """)
    
    with col3:
        st.markdown("""
        **📊 Analytics**
        
        PageRank and community detection insights
        """)
    
    with col4:
        st.markdown("""
        **📈 Trends**
        
        Time-series analysis of relationship patterns
        """)
    
    st.divider()
    
    # Quick Statistics Dashboard
    st.markdown("### 📊 Network Statistics")
    
    try:
        if app.graph_manager:
            graph = app.graph_manager.get_graph()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Entities", graph.number_of_nodes())
            
            with col2:
                st.metric("Total Relationships", graph.number_of_edges())
            
            with col3:
                if graph.number_of_nodes() > 0:
                    avg_degree = sum(dict(graph.degree()).values()) / graph.number_of_nodes()
                    st.metric("Avg. Connections", f"{avg_degree:.1f}")
                else:
                    st.metric("Avg. Connections", "0")
            
            with col4:
                try:
                    total_articles = app.db_handler.get_article_count()
                    st.metric("Total Articles", total_articles)
                except:
                    st.metric("Total Articles", "N/A")
            
            st.divider()
            
            # Top Influential Entities (PageRank)
            st.markdown("### 🏆 Top Influential Entities")
            
            pagerank_results = app.compute_pagerank()
            if pagerank_results:
                top_5 = pagerank_results[:5]
                
                # Display as cards
                cols = st.columns(5)
                for idx, entity in enumerate(top_5):
                    with cols[idx]:
                        st.metric(
                            label=entity.entity_name[:20] + ("..." if len(entity.entity_name) > 20 else ""),
                            value=f"{entity.score:.4f}",
                            delta=f"{entity.entity_type}"
                        )
                
                # Bar chart
                df_pagerank = pd.DataFrame([
                    {
                        'Entity': e.entity_name,
                        'PageRank Score': e.score,
                        'Type': e.entity_type
                    }
                    for e in pagerank_results[:10]
                ])
                
                fig = px.bar(
                    df_pagerank,
                    x='PageRank Score',
                    y='Entity',
                    orientation='h',
                    color='Type',
                    title="Top 10 Entities by PageRank",
                    labels={'PageRank Score': 'PageRank Score', 'Entity': 'Entity Name'}
                )
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No PageRank data available. Please ensure the graph has been built.")
            
            st.divider()
            
            # Entity Type Distribution
            st.markdown("### 📊 Entity Type Distribution")
            
            entity_types = {}
            for node, data in graph.nodes(data=True):
                entity_type = data.get('type', 'Unknown')
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            if entity_types:
                df_types = pd.DataFrame([
                    {'Type': k, 'Count': v}
                    for k, v in entity_types.items()
                ])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_pie = px.pie(
                        df_types,
                        values='Count',
                        names='Type',
                        title="Entity Types"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    fig_bar = px.bar(
                        df_types,
                        x='Type',
                        y='Count',
                        title="Entity Type Counts"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            st.divider()
            
            # Relationship Type Distribution
            st.markdown("### 🔗 Relationship Type Distribution")
            
            rel_types = {}
            for u, v, data in graph.edges(data=True):
                rel_type = data.get('relationship_type', 'Unknown')
                rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
            
            if rel_types:
                df_rels = pd.DataFrame([
                    {'Relationship Type': k, 'Count': v}
                    for k, v in sorted(rel_types.items(), key=lambda x: x[1], reverse=True)
                ])
                
                fig = px.bar(
                    df_rels,
                    x='Relationship Type',
                    y='Count',
                    title="Relationship Types"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # Recent Activity
            st.markdown("### 📰 Recent Activity")
            
            try:
                # Get latest articles
                articles = app.db_handler.get_all_articles(limit=5)
                
                if articles:
                    st.markdown("#### Latest Articles")
                    for article in articles:
                        with st.expander(f"**{article.get('headline', 'No headline')}**"):
                            st.write(f"**Source:** {article.get('source', 'Unknown')}")
                            st.write(f"**Date:** {article.get('publication_date', 'Unknown')}")
                            st.write(f"**URL:** {article.get('url', 'N/A')}")
                else:
                    st.info("No articles found")
            except Exception as e:
                st.warning(f"Could not load recent articles: {e}")
            
            # Community Detection Snapshot
            st.markdown("#### Community Detection Snapshot")
            communities = app.detect_communities()
            if communities:
                top_communities = sorted(communities, key=lambda x: x.size, reverse=True)[:3]
                for comm in top_communities:
                    st.info(f"**Community {comm.community_id}**: {comm.size} entities - {comm.description}")
            else:
                st.info("No communities detected")
        
        else:
            st.warning("Graph manager not available. Please ensure the graph database exists.")
    
    except Exception as e:
        st.error(f"Error loading dashboard data: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()

