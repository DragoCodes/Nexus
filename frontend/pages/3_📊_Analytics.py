"""Analytics page for PageRank and Community Detection."""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.module5_api.app import NexusApp


@st.cache_resource
def get_app():
    """Get NexusApp instance."""
    return NexusApp()


def main():
    """Main function for Analytics page."""
    st.title("📊 Analytics")
    st.markdown("PageRank influence analysis and community detection")
    
    # Get app instance
    app = get_app()
    
    if app is None or app.graph_analytics is None:
        st.error("Graph analytics not available. Please ensure the graph database exists.")
        st.info("You may need to run Module 4 to build the graph first.")
        st.stop()
    
    # Create tabs
    tab1, tab2 = st.tabs(["📈 PageRank (Influence Analysis)", "👥 Community Detection"])
    
    with tab1:
        show_pagerank_tab(app)
    
    with tab2:
        show_communities_tab(app)


def show_pagerank_tab(app):
    """Display PageRank analysis tab."""
    st.header("PageRank Influence Analysis")
    
    st.markdown("""
    **PageRank** identifies the most influential entities in the knowledge graph based on their connections.
    Entities with high PageRank scores are central to the network and have strong connections to other important entities.
    """)
    
    st.divider()
    
    # Compute PageRank
    with st.spinner("Computing PageRank..."):
        pagerank_results = app.compute_pagerank()
    
    if not pagerank_results:
        st.warning("No PageRank results available. The graph may be empty.")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        entity_type_filter = st.selectbox(
            "Filter by Entity Type",
            options=["All"] + list(set(e.entity_type for e in pagerank_results)),
            index=0
        )
    
    with col2:
        top_n = st.slider(
            "Top N Entities",
            min_value=10,
            max_value=min(50, len(pagerank_results)),
            value=20,
            step=5
        )
    
    # Filter results
    filtered_results = pagerank_results
    if entity_type_filter != "All":
        filtered_results = [e for e in pagerank_results if e.entity_type == entity_type_filter]
    
    filtered_results = filtered_results[:top_n]
    
    st.divider()
    
    # Top Influential Entities
    st.subheader(f"Top {len(filtered_results)} Influential Entities")
    
    # Create DataFrame
    df_pagerank = pd.DataFrame([
        {
            'Rank': idx + 1,
            'Entity Name': e.entity_name,
            'Entity Type': e.entity_type,
            'PageRank Score': e.score
        }
        for idx, e in enumerate(filtered_results)
    ])
    
    # Display table
    st.dataframe(
        df_pagerank,
        use_container_width=True,
        hide_index=True
    )
    
    # Visualization
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        # Bar chart
        fig_bar = px.bar(
            df_pagerank.head(10),
            x='PageRank Score',
            y='Entity Name',
            orientation='h',
            color='Entity Type',
            title="Top 10 Entities by PageRank",
            labels={'PageRank Score': 'PageRank Score', 'Entity Name': 'Entity Name'}
        )
        fig_bar.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_viz2:
        # Score distribution by type
        df_by_type = df_pagerank.groupby('Entity Type')['PageRank Score'].mean().reset_index()
        df_by_type = df_by_type.sort_values('PageRank Score', ascending=False)
        
        fig_pie = px.pie(
            df_by_type,
            values='PageRank Score',
            names='Entity Type',
            title="Average PageRank by Entity Type"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Insights
    st.divider()
    st.subheader("💡 Insights")
    
    if filtered_results:
        # Most influential entity
        top_entity = filtered_results[0]
        st.info(f"**Most influential entity:** {top_entity.entity_name} ({top_entity.entity_type}) with PageRank score {top_entity.score:.6f}")
        
        # Top 3 entities
        top_3 = filtered_results[:3]
        st.markdown("**Top 3 most influential entities:**")
        for idx, entity in enumerate(top_3, 1):
            st.markdown(f"{idx}. {entity.entity_name} ({entity.entity_type}) - Score: {entity.score:.6f}")
        
        # Entity type distribution in top N
        type_counts = {}
        for entity in filtered_results:
            entity_type = entity.entity_type
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        if type_counts:
            top_type = max(type_counts.items(), key=lambda x: x[1])
            st.info(f"**Most common entity type in top {len(filtered_results)}:** {top_type[0]} ({top_type[1]} entities)")
        
        # Score statistics
        scores = [e.score for e in filtered_results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Average Score", f"{avg_score:.6f}")
        with col_stat2:
            st.metric("Maximum Score", f"{max_score:.6f}")
        with col_stat3:
            st.metric("Minimum Score", f"{min_score:.6f}")
    
    # Export button
    st.divider()
    if st.button("📥 Export to CSV", use_container_width=True):
        csv = df_pagerank.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="pagerank_results.csv",
            mime="text/csv"
        )


def show_communities_tab(app):
    """Display Community Detection tab."""
    st.header("Community Detection")
    
    st.markdown("""
    **Communities** are groups of entities that are closely connected to each other.
    These communities often represent business ecosystems, supply chains, or competitive clusters.
    """)
    
    st.divider()
    
    # Detect communities
    with st.spinner("Detecting communities..."):
        communities = app.detect_communities()
    
    if not communities:
        st.warning("No communities detected. The graph may be too small or disconnected.")
        return
    
    # Sort by size
    communities = sorted(communities, key=lambda x: x.size, reverse=True)
    
    st.subheader(f"Found {len(communities)} Communities")
    
    # Community comparison table
    st.markdown("### Community Comparison")
    
    df_communities = pd.DataFrame([
        {
            'Community ID': c.community_id,
            'Size': c.size,
            'Description': c.description,
            'Dominant Types': ', '.join([f"{k} ({v})" for k, v in list(c.dominant_types.items())[:3]])
        }
        for c in communities
    ])
    
    st.dataframe(
        df_communities,
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # Community cards
    st.subheader("Community Details")
    
    # Filter by size
    min_size = st.slider(
        "Minimum Community Size",
        min_value=1,
        max_value=max([c.size for c in communities] if communities else [1]),
        value=2,
        step=1
    )
    
    filtered_communities = [c for c in communities if c.size >= min_size]
    
    # Display community cards
    for comm in filtered_communities:
        with st.expander(f"**Community {comm.community_id}** - {comm.size} entities - {comm.description}", expanded=False):
            col_card1, col_card2 = st.columns([2, 1])
            
            with col_card1:
                st.markdown(f"**Size:** {comm.size} entities")
                st.markdown(f"**Description:** {comm.description}")
                
                # Dominant types
                if comm.dominant_types:
                    st.markdown("**Entity Type Distribution:**")
                    type_df = pd.DataFrame([
                        {'Type': k, 'Count': v}
                        for k, v in comm.dominant_types.items()
                    ])
                    st.dataframe(type_df, use_container_width=True, hide_index=True)
            
            with col_card2:
                # Show top entities
                st.markdown("**Top Entities:**")
                top_entities = comm.entities[:10]
                for entity in top_entities:
                    st.caption(f"• {entity}")
                
                if len(comm.entities) > 10:
                    st.caption(f"... and {len(comm.entities) - 10} more")
                
                # View in Graph button
                if st.button(f"🕸️ View in Graph", key=f"view_comm_{comm.community_id}", use_container_width=True):
                    st.session_state.community_filter = comm.community_id
                    st.info("💡 Use the sidebar navigation to go to '🕸️ Knowledge Graph' page to view this community")
        
        st.divider()
    
    # Visualization
    st.subheader("Community Visualization")
    
    # Size distribution
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        sizes = [c.size for c in communities]
        fig_hist = px.histogram(
            x=sizes,
            nbins=20,
            title="Community Size Distribution",
            labels={'x': 'Community Size', 'y': 'Count'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col_viz2:
        # Size vs count
        size_counts = {}
        for c in communities:
            size_counts[c.size] = size_counts.get(c.size, 0) + 1
        
        df_size = pd.DataFrame([
            {'Size': k, 'Count': v}
            for k, v in sorted(size_counts.items())
        ])
        
        fig_bar = px.bar(
            df_size,
            x='Size',
            y='Count',
            title="Community Size Distribution"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Insights
    st.divider()
    st.subheader("💡 Insights")
    
    if communities:
        largest_comm = communities[0]
        st.info(f"**Largest community:** Community {largest_comm.community_id} with {largest_comm.size} entities - {largest_comm.description}")
        
        avg_size = sum(c.size for c in communities) / len(communities)
        st.info(f"**Average community size:** {avg_size:.1f} entities")
        
        total_entities = sum(c.size for c in communities)
        st.info(f"**Total entities in communities:** {total_entities}")
        
        # Most common entity type across communities
        all_types = {}
        for c in communities:
            for entity_type, count in c.dominant_types.items():
                all_types[entity_type] = all_types.get(entity_type, 0) + count
        
        if all_types:
            most_common_type = max(all_types.items(), key=lambda x: x[1])
            st.info(f"**Most common entity type:** {most_common_type[0]} (appears in {most_common_type[1]} entities across communities)")
    
    # Export button
    st.divider()
    if st.button("📥 Export Communities to CSV", use_container_width=True):
        # Flatten communities data
        export_data = []
        for c in communities:
            for entity in c.entities:
                export_data.append({
                    'Community ID': c.community_id,
                    'Entity': entity,
                    'Community Size': c.size,
                    'Description': c.description
                })
        
        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="communities.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()

