"""News Search page for searching articles."""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.module5_api.app import NexusApp


@st.cache_resource
def get_app():
    """Get NexusApp instance."""
    return NexusApp()


def highlight_text(text: str, query_terms: list) -> str:
    """Highlight query terms in text."""
    if not query_terms or not text:
        return text
    
    # Create regex pattern for highlighting
    pattern = '|'.join(re.escape(term) for term in query_terms if len(term) > 2)
    if not pattern:
        return text
    
    # Highlight matches (case insensitive)
    highlighted = re.sub(
        f'({pattern})',
        r'<mark style="background-color: yellow;">\1</mark>',
        text,
        flags=re.IGNORECASE
    )
    return highlighted


def main():
    """Main function for News Search page."""
    st.title("📰 News Search")
    st.markdown("Search financial news articles using BM25 ranking algorithm")
    
    # Get app instance
    app = get_app()
    
    if app is None:
        st.error("Failed to initialize application. Please check your configuration.")
        st.stop()
    
    # Search Interface
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Search Query",
                placeholder="Search financial news... (e.g., 'Tesla merger', 'NVIDIA partnership')",
                label_visibility="collapsed"
            )
        
        with col2:
            num_results = st.selectbox(
                "Results",
                [10, 20, 50],
                index=0,
                label_visibility="collapsed"
            )
        
        col3, col4 = st.columns([1, 1])
        with col3:
            search_button = st.form_submit_button("🔍 Search", use_container_width=True)
        with col4:
            clear_button = st.form_submit_button("Clear", use_container_width=True)
        
        # Advanced options
        with st.expander("Advanced Options"):
            col5, col6 = st.columns(2)
            
            with col5:
                date_from = st.date_input(
                    "From Date",
                    value=datetime.now() - timedelta(days=30),
                    max_value=datetime.now()
                )
            
            with col6:
                date_to = st.date_input(
                    "To Date",
                    value=datetime.now(),
                    max_value=datetime.now()
                )
            
            source_filter = st.text_input(
                "Source Filter",
                placeholder="e.g., Reuters, Bloomberg (leave empty for all)"
            )
    
    # Handle clear button
    if clear_button:
        st.session_state.search_results = None
        st.session_state.search_query = None
        st.rerun()
    
    # Perform search
    if search_button and query:
        with st.spinner(f"Searching for '{query}'..."):
            results = app.search_articles(query, k=num_results)
            
            if results:
                st.session_state.search_results = results
                st.session_state.search_query = query
                st.success(f"Found {len(results)} results")
            else:
                st.session_state.search_results = []
                st.session_state.search_query = query
                st.info("No results found. Try different search terms.")
    
    # Display results
    if 'search_results' in st.session_state and st.session_state.search_results:
        results = st.session_state.search_results
        query = st.session_state.get('search_query', '')
        
        st.divider()
        st.markdown(f"### Search Results ({len(results)} found)")
        
        # Extract query terms for highlighting
        query_terms = query.lower().split() if query else []
        
        # Display each result
        for idx, result in enumerate(results, 1):
            with st.container():
                # Create columns for result card
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # Headline (clickable)
                    headline = result.headline
                    if result.url:
                        st.markdown(f"### [{headline}]({result.url})")
                    else:
                        st.markdown(f"### {headline}")
                    
                    # Metadata
                    col_meta1, col_meta2, col_meta3 = st.columns(3)
                    with col_meta1:
                        st.caption(f"📅 {result.publication_date.strftime('%Y-%m-%d') if isinstance(result.publication_date, datetime) else result.publication_date}")
                    with col_meta2:
                        st.caption(f"📰 {result.source}")
                    with col_meta3:
                        st.caption(f"⭐ Score: {result.score:.4f}")
                    
                    # Excerpt (would need to fetch from MongoDB)
                    st.caption(f"Article ID: {result.article_id}")
                
                with col2:
                    # View in Graph button
                    if app.graph_manager:
                        if st.button("🕸️ View in Graph", key=f"view_graph_{idx}", use_container_width=True):
                            st.session_state.selected_article_id = result.article_id
                            st.info("💡 Use the sidebar navigation to go to '🕸️ Knowledge Graph' page to view this article's entities")
                
                st.divider()
        
        # Pagination (if more than 50 results)
        if len(results) >= 50:
            st.info("Showing top 50 results. Refine your search for more specific results.")
    
    elif 'search_results' in st.session_state and st.session_state.search_results == []:
        st.info("No results found. Try:")
        st.markdown("""
        - Using different keywords
        - Checking spelling
        - Using more general terms
        - Removing filters
        """)
    
    else:
        # Empty state
        st.info("Enter a search query above to find articles.")
        st.markdown("### Example Searches:")
        example_searches = [
            "Tesla merger",
            "NVIDIA partnership",
            "stock market",
            "IPO announcement",
            "CEO resignation",
            "investment funding"
        ]
        
        cols = st.columns(3)
        for idx, example in enumerate(example_searches):
            with cols[idx % 3]:
                if st.button(f"🔍 {example}", key=f"example_{idx}", use_container_width=True):
                    st.session_state.search_query = example
                    st.rerun()


if __name__ == "__main__":
    main()

