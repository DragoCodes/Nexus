"""Trends page for time-series analysis of relationships."""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
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
    """Main function for Trends page."""
    st.title("📈 Trends")
    st.markdown("Time-series analysis of relationship patterns")
    
    # Get app instance
    app = get_app()
    
    if app is None or app.graph_manager is None:
        st.error("Graph manager not available. Please ensure the graph database exists.")
        st.info("You may need to run Module 4 to build the graph first.")
        st.stop()
    
    # Get graph to extract relationship types
    graph = app.graph_manager.get_graph()
    
    if graph.number_of_edges() == 0:
        st.warning("No relationships found. Please build the graph first.")
        st.stop()
    
    # Get all relationship types
    rel_types = set()
    for u, v, data in graph.edges(data=True):
        rel_type = data.get('relationship_type', 'Unknown')
        rel_types.add(rel_type)
    
    if not rel_types:
        st.warning("No relationship types found.")
        st.stop()
    
    # Controls
    st.sidebar.header("📊 Controls")
    
    # Relationship type selector
    selected_rel_types = st.sidebar.multiselect(
        "Relationship Types",
        options=sorted(rel_types),
        default=list(sorted(rel_types))[:3] if len(rel_types) >= 3 else list(sorted(rel_types)),
        help="Select relationship types to analyze"
    )
    
    if not selected_rel_types:
        st.warning("Please select at least one relationship type.")
        st.stop()
    
    # Date range picker
    st.sidebar.subheader("Date Range")
    
    # Get date range from graph
    all_dates = []
    for u, v, data in graph.edges(data=True):
        pub_dates = data.get('publication_dates', [])
        if isinstance(pub_dates, str):
            try:
                import json
                pub_dates = json.loads(pub_dates)
            except:
                pub_dates = []
        if isinstance(pub_dates, list):
            all_dates.extend(pub_dates)
    
    if all_dates:
        try:
            # Parse dates
            parsed_dates = []
            for date_str in all_dates:
                try:
                    if isinstance(date_str, str):
                        # Try parsing ISO format
                        parsed_dates.append(datetime.fromisoformat(date_str.replace('Z', '+00:00')))
                    elif isinstance(date_str, datetime):
                        parsed_dates.append(date_str)
                except:
                    continue
            
            if parsed_dates:
                min_date = min(parsed_dates).date()
                max_date = max(parsed_dates).date()
            else:
                min_date = datetime.now().date() - timedelta(days=30)
                max_date = datetime.now().date()
        except:
            min_date = datetime.now().date() - timedelta(days=30)
            max_date = datetime.now().date()
    else:
        min_date = datetime.now().date() - timedelta(days=30)
        max_date = datetime.now().date()
    
    date_from = st.sidebar.date_input(
        "From Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    
    date_to = st.sidebar.date_input(
        "To Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    
    # Aggregation level
    aggregation = st.sidebar.selectbox(
        "Aggregation Level",
        options=["Daily", "Weekly", "Monthly"],
        index=0
    )
    
    # Entity filter (optional)
    st.sidebar.subheader("Entity Filter (Optional)")
    all_entities = app.get_all_entities()
    entity_names = [e['entity_name'] for e in all_entities[:100]]  # Limit for performance
    
    selected_entity = st.sidebar.selectbox(
        "Filter by Entity",
        options=["None"] + entity_names,
        help="Show trends for specific entity only"
    )
    
    st.divider()
    
    # Get trend data
    with st.spinner("Loading trend data..."):
        trend_data = []
        
        for rel_type in selected_rel_types:
            trends = app.get_relationship_trends(
                relationship_type=rel_type,
                start_date=date_from.isoformat(),
                end_date=date_to.isoformat()
            )
            
            for trend in trends:
                trend_data.append({
                    'date': trend.date,
                    'count': trend.count,
                    'relationship_type': trend.relationship_type
                })
    
    if not trend_data:
        st.info("No trend data available for the selected filters.")
        st.markdown("""
        **Possible reasons:**
        - No relationships match the selected types and date range
        - Date range is too narrow
        - Graph needs to be rebuilt with more data
        """)
        return
    
    # Convert to DataFrame
    df_trends = pd.DataFrame(trend_data)
    
    # Parse dates
    df_trends['date'] = pd.to_datetime(df_trends['date'])
    
    # Filter by entity if selected
    if selected_entity != "None":
        # Filter relationships involving the selected entity
        filtered_data = []
        for u, v, data in graph.edges(data=True):
            if u == selected_entity or v == selected_entity:
                rel_type = data.get('relationship_type', 'Unknown')
                if rel_type in selected_rel_types:
                    pub_dates = data.get('publication_dates', [])
                    if isinstance(pub_dates, str):
                        try:
                            import json
                            pub_dates = json.loads(pub_dates)
                        except:
                            pub_dates = []
                    
                    for date_str in pub_dates:
                        try:
                            if isinstance(date_str, str):
                                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            else:
                                date_obj = date_str
                            
                            if date_from <= date_obj.date() <= date_to:
                                filtered_data.append({
                                    'date': date_obj,
                                    'count': 1,
                                    'relationship_type': rel_type
                                })
                        except:
                            continue
        
        if filtered_data:
            df_trends = pd.DataFrame(filtered_data)
            df_trends['date'] = pd.to_datetime(df_trends['date'])
        else:
            st.warning(f"No data found for entity '{selected_entity}' with selected filters.")
            return
    
    # Aggregate by date
    if aggregation == "Daily":
        df_agg = df_trends.groupby(['date', 'relationship_type']).sum().reset_index()
        df_agg['date'] = df_agg['date'].dt.date
    elif aggregation == "Weekly":
        df_trends['week'] = df_trends['date'].dt.to_period('W').dt.start_time
        df_agg = df_trends.groupby(['week', 'relationship_type']).sum().reset_index()
        df_agg['date'] = df_agg['week'].dt.date
        df_agg = df_agg.drop(columns=['week'])
    else:  # Monthly
        df_trends['month'] = df_trends['date'].dt.to_period('M').dt.start_time
        df_agg = df_trends.groupby(['month', 'relationship_type']).sum().reset_index()
        df_agg['date'] = df_agg['month'].dt.date
        df_agg = df_agg.drop(columns=['month'])
    
    # Ensure no duplicates (group by date and relationship_type again after date conversion)
    df_agg = df_agg.groupby(['date', 'relationship_type']).sum().reset_index()
    
    # Sort by date
    df_agg = df_agg.sort_values('date')
    
    # Main Visualization
    st.subheader("Relationship Frequency Over Time")
    
    # Line chart
    fig = px.line(
        df_agg,
        x='date',
        y='count',
        color='relationship_type',
        title=f"Relationship Trends ({aggregation})",
        labels={'date': 'Date', 'count': 'Count', 'relationship_type': 'Relationship Type'},
        markers=True
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Insights Panel
    st.divider()
    st.subheader("💡 Insights")
    
    col_insight1, col_insight2, col_insight3 = st.columns(3)
    
    with col_insight1:
        # Peak dates
        if len(df_agg) > 0:
            peak_row = df_agg.loc[df_agg['count'].idxmax()]
            st.metric(
                "Peak Activity",
                f"{peak_row['count']}",
                delta=f"{peak_row['date']} ({peak_row['relationship_type']})"
            )
    
    with col_insight2:
        # Total count
        total_count = df_agg['count'].sum()
        st.metric("Total Relationships", total_count)
    
    with col_insight3:
        # Average per period
        if len(df_agg) > 0:
            avg_count = df_agg['count'].mean()
            st.metric("Average per Period", f"{avg_count:.1f}")
    
    # Trend direction
    if len(df_agg) > 1:
        first_half = df_agg.head(len(df_agg) // 2)['count'].mean()
        second_half = df_agg.tail(len(df_agg) - len(df_agg) // 2)['count'].mean()
        
        trend_direction = "Increasing" if second_half > first_half else "Decreasing"
        trend_change = abs(second_half - first_half)
        
        st.info(f"**Trend Direction:** {trend_direction} (change: {trend_change:.1f} relationships per period)")
    
    # Anomalies
    if len(df_agg) > 2:
        mean_count = df_agg['count'].mean()
        std_count = df_agg['count'].std()
        
        if std_count > 0:
            threshold = mean_count + 2 * std_count
            anomalies = df_agg[df_agg['count'] > threshold]
            
            if len(anomalies) > 0:
                st.warning(f"**Anomalies detected:** {len(anomalies)} periods with unusually high activity")
                with st.expander("View Anomalies"):
                    st.dataframe(anomalies, use_container_width=True)
    
    # Comparison Mode
    st.divider()
    st.subheader("Comparison Mode")
    
    if len(selected_rel_types) > 1:
        # Compare relationship types
        # Use pivot_table to handle any duplicate entries by summing them
        comparison_df = df_agg.pivot_table(
            index='date', 
            columns='relationship_type', 
            values='count', 
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        st.markdown("### Relationship Type Comparison")
        # Melt the pivoted dataframe for plotting
        comparison_melted = comparison_df.melt(
            id_vars='date',
            value_vars=[col for col in comparison_df.columns if col != 'date'],
            var_name='relationship_type',
            value_name='count'
        )
        fig_comparison = px.bar(
            comparison_melted,
            x='date',
            y='count',
            color='relationship_type',
            title="Relationship Types Comparison",
            labels={'value': 'Count', 'date': 'Date', 'relationship_type': 'Relationship Type'}
        )
        fig_comparison.update_layout(
            height=500,
            xaxis_title="Date",
            yaxis_title="Count",
            hovermode='x unified'
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Data Table
    st.divider()
    st.subheader("Data Table")
    
    st.dataframe(
        df_agg,
        use_container_width=True,
        hide_index=True
    )
    
    # Export button
    st.divider()
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📥 Export to CSV", use_container_width=True):
            csv = df_agg.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"trends_{aggregation.lower()}.csv",
                mime="text/csv"
            )
    
    with col_export2:
        if st.button("📊 Export Chart", use_container_width=True):
            st.info("Right-click on the chart above and select 'Download plot as PNG' to save the visualization.")


if __name__ == "__main__":
    main()

