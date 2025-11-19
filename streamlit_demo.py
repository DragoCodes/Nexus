"""
Streamlit front-end for Nexus demo.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from pyvis.network import Network
import tempfile
import os


API_BASE = os.getenv("NEXUS_API_BASE", "http://localhost:5000")


# Company logo mapping - using Clearbit logo API
def get_company_logo_url(company_name: str) -> str:
    """Get company logo URL from Clearbit API"""
    # Map common company names to their domains
    company_domains = {
        "NVIDIA": "nvidia.com",
        "Apple": "apple.com",
        "Microsoft": "microsoft.com",
        "Amazon": "amazon.com",
        "Alphabet": "google.com",
        "TSMC": "tsmc.com",
        "Intel": "intel.com",
        "AMD": "amd.com",
        "Samsung": "samsung.com",
        "ASML": "asml.com",
        "Meta": "meta.com",
        "Tesla": "tesla.com",
        "Oracle": "oracle.com",
        "IBM": "ibm.com",
    }
    
    domain = company_domains.get(company_name, company_name.lower().replace(" ", "") + ".com")
    return f"https://logo.clearbit.com/{domain}"


def get_node_color(entity_type: str) -> str:
    """Get color based on entity type"""
    colors = {
        "Company": "#4A90E2",  # Blue
        "Person": "#F5A623",   # Orange
        "Product": "#7ED321",  # Green
    }
    return colors.get(entity_type, "#BDC3C7")  # Gray default


st.set_page_config(page_title="Nexus Demo", layout="wide")
st.title("🔷 Nexus – Financial Knowledge Graph")


def _fetch_json(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{API_BASE}{path}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
        return {}


with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base URL", value=API_BASE)
    if api_base != API_BASE:
        API_BASE = api_base
    k_value = st.slider("Results per query", min_value=3, max_value=20, value=10, step=1)


tab_search, tab_entity, tab_graph, tab_analytics = st.tabs(
    ["Search Articles", "Entity Explorer", "Graph Visualization", "Analytics"]
)


with tab_search:
    query = st.text_input("Query", placeholder='e.g., "NVIDIA partnership"')
    if query:
        data = _fetch_json("/api/search/search", params={"q": query, "k": k_value})
        results: List[Dict[str, Any]] = data.get("results", [])
        st.caption(f"{len(results)} of {data.get('total_documents', 0)} documents shown.")
        for result in results:
            st.subheader(result["headline"])
            st.write(
                f"Score: **{result['bm25_score']:.2f}** · Source: {result['source']} "
                f"· Date: {result['publication_date']}"
            )
            st.write(result["snippet"])
            
            # Try to get entities from the article's extraction
            article_id = result.get("article_id")
            entities_data = _fetch_json(f"/api/graph/article/{article_id}/entities")
            entities = entities_data.get("entities", [])
            
            if entities:
                # If we have entities, show a dropdown to select one
                selected_entity = st.selectbox(
                    "View entity in graph:",
                    options=entities,
                    key=f"entity_select_{article_id}",
                    index=0
                )
                if st.button("View in graph", key=f"view_{article_id}"):
                    st.session_state["selected_entity"] = selected_entity
                    st.session_state["auto_fetch_entity"] = True
                    st.success(f"✅ Selected entity: **{selected_entity}**. Switch to 'Entity Explorer' tab to view.")
            else:
                # Fallback: try to extract entity from headline (look for common company names)
                if st.button("View in graph", key=f"view_{article_id}"):
                    # Try common entity names that might be in the headline
                    common_entities = ["NVIDIA", "Apple", "Microsoft", "Amazon", "Alphabet", "TSMC", "Intel", "AMD", "Samsung", "ASML"]
                    headline_words = result["headline"].upper().split()
                    found_entity = None
                    for entity in common_entities:
                        if entity.upper() in headline_words:
                            found_entity = entity
                            break
                    
                    if found_entity:
                        st.session_state["selected_entity"] = found_entity
                        st.session_state["auto_fetch_entity"] = True
                        st.success(f"✅ Selected entity: **{found_entity}**. Switch to 'Entity Explorer' tab to view.")
                    else:
                        # Use first capitalized word as fallback
                        first_word = result["headline"].split()[0]
                        st.session_state["selected_entity"] = first_word
                        st.session_state["auto_fetch_entity"] = True
                        st.warning(f"⚠️ Could not find entity in extraction. Trying '{first_word}'. Switch to 'Entity Explorer' tab to view.")
    else:
        st.info("Enter a query to search articles.")


with tab_entity:
    default_entity = st.session_state.get("selected_entity", "NVIDIA")
    entity_name = st.text_input("Entity name", value=default_entity)
    
    # Auto-fetch if "View in graph" was clicked
    auto_fetch = st.session_state.get("auto_fetch_entity", False)
    if auto_fetch:
        st.session_state["auto_fetch_entity"] = False  # Reset flag
        entity_data = _fetch_json(f"/api/graph/entity/{entity_name}")
        if "error" not in entity_data:
            st.success(f"✅ Found entity: **{entity_name}**")
            st.json(entity_data)
        else:
            st.warning(f"Entity '{entity_name}' not found in graph. {entity_data.get('error', '')}")
    elif st.button("Fetch entity"):
        entity_data = _fetch_json(f"/api/graph/entity/{entity_name}")
        if "error" not in entity_data:
            st.json(entity_data)
        else:
            st.warning(entity_data["error"])
    
    # Show available entities
    if st.checkbox("Show all entities in graph"):
        stats = _fetch_json("/api/graph/stats")
        if "error" not in stats:
            st.info(f"Graph contains {stats.get('nodes', 0)} entities. Try searching for: NVIDIA, Apple, Microsoft, TSMC, etc.")


with tab_graph:
    st.header("🔗 Interactive Knowledge Graph Visualization")
    
    # Fetch graph data
    graph_data = _fetch_json("/api/graph/visualization")
    
    if "error" in graph_data:
        st.error(f"Failed to load graph: {graph_data.get('error')}")
    elif graph_data.get("nodes"):
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        stats = graph_data.get("stats", {})
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Entities", stats.get('nodes', 0))
        with col_stat2:
            st.metric("Relationships", stats.get('edges', 0))
        with col_stat3:
            st.metric("Relationship Types", stats.get('relationships', 0))
        
        # Create NetworkX graph for layout calculation
        G = nx.DiGraph()
        
        # Add nodes with metadata
        node_dict = {}
        for node in nodes:
            node_id = node["id"]
            G.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})
            node_dict[node_id] = node
        
        # Add edges
        for edge in edges:
            G.add_edge(
                edge["source"],
                edge["target"],
                relationship=edge.get("relationship", ""),
                count=edge.get("count", 1)
            )
        
        # Controls sidebar
        with st.sidebar:
            st.subheader("🎨 Visualization Controls")
            
            layout_type = st.selectbox(
                "Layout Algorithm",
                ["Spring", "Circular", "Force-Directed", "Hierarchical"],
                index=0
            )
            
            node_size_factor = st.slider("Node Size", min_value=10, max_value=50, value=20)
            edge_width_factor = st.slider("Edge Width", min_value=1, max_value=10, value=3)
            
            st.divider()
            st.subheader("🔍 Filters")
            
            min_degree = st.slider("Min Node Degree", min_value=0, max_value=50, value=0)
            
            all_relationships = ["All"] + sorted(list(set(e.get("relationship", "") for e in edges)))
            selected_relationship = st.selectbox(
                "Filter by Relationship",
                all_relationships,
                index=0
            )
            
            entity_types = ["All"] + sorted(list(set(n.get("type", "Unknown") for n in nodes)))
            selected_type = st.selectbox(
                "Filter by Entity Type",
                entity_types,
                index=0
            )
        
        # Apply filters
        filtered_G = G.copy()
        
        if min_degree > 0:
            nodes_to_remove = [n for n in filtered_G.nodes() if filtered_G.degree(n) < min_degree]
            filtered_G.remove_nodes_from(nodes_to_remove)
        
        if selected_relationship != "All":
            edges_to_remove = [
                (u, v) for u, v, d in filtered_G.edges(data=True)
                if d.get("relationship") != selected_relationship
            ]
            filtered_G.remove_edges_from(edges_to_remove)
            isolated = list(nx.isolates(filtered_G))
            filtered_G.remove_nodes_from(isolated)
        
        if selected_type != "All":
            nodes_to_remove = [
                n for n in filtered_G.nodes()
                if node_dict.get(n, {}).get("type") != selected_type
            ]
            filtered_G.remove_nodes_from(nodes_to_remove)
            isolated = list(nx.isolates(filtered_G))
            filtered_G.remove_nodes_from(isolated)
        
        if filtered_G.number_of_nodes() == 0:
            st.warning("No nodes match the filter criteria. Adjust filters.")
        else:
            # Visualization type selector
            viz_type = st.radio(
                "Visualization Type",
                ["Interactive Graph with Logos (Pyvis)", "Plotly Graph"],
                index=0,
                horizontal=True
            )
            
            if viz_type == "Interactive Graph with Logos (Pyvis)":
                # Use pyvis for logo support
                net = Network(
                    height='700px',
                    width='100%',
                    bgcolor='#fafafa',
                    font_color='#2C3E50',
                    directed=True,
                    notebook=False
                )
                
                # Enhanced configuration for better aesthetics
                physics_config = {
                    "enabled": True,
                    "barnesHut": {
                        "gravitationalConstant": -3000,
                        "centralGravity": 0.08,
                        "springLength": 250,
                        "springConstant": 0.04,
                        "damping": 0.15
                    },
                    "minVelocity": 0.75,
                    "solver": "barnesHut",
                    "stabilization": {
                        "enabled": True,
                        "iterations": 200,
                        "updateInterval": 25
                    }
                }
                
                if layout_type == "Spring":
                    net.set_options(f"""
                    {{
                      "physics": {{
                        "enabled": true,
                        "barnesHut": {{
                          "gravitationalConstant": -3000,
                          "centralGravity": 0.08,
                          "springLength": 250,
                          "springConstant": 0.04,
                          "damping": 0.15
                        }},
                        "minVelocity": 0.75,
                        "solver": "barnesHut",
                        "stabilization": {{
                          "enabled": true,
                          "iterations": 200
                        }}
                      }},
                      "interaction": {{
                        "hover": true,
                        "tooltipDelay": 100,
                        "hideEdgesOnDrag": false,
                        "hideEdgesOnZoom": false
                      }},
                      "edges": {{
                        "smooth": {{
                          "type": "continuous",
                          "roundness": 0.5
                        }},
                        "arrows": {{
                          "to": {{
                            "enabled": true,
                            "scaleFactor": 0.8
                          }}
                        }},
                        "color": {{
                          "color": "#b0b0b0",
                          "highlight": "#4A90E2",
                          "hover": "#6BB6FF"
                        }},
                        "font": {{
                          "size": 11,
                          "face": "Arial",
                          "color": "#666666"
                        }}
                      }},
                      "nodes": {{
                        "font": {{
                          "size": 12,
                          "face": "Arial",
                          "color": "#2C3E50",
                          "bold": true
                        }},
                        "borderWidth": 2,
                        "shadow": {{
                          "enabled": true,
                          "color": "rgba(0,0,0,0.1)",
                          "size": 5,
                          "x": 2,
                          "y": 2
                        }}
                      }}
                    }}
                    """)
                elif layout_type == "Circular":
                    net.set_options("""
                    {
                      "layout": {
                        "hierarchical": {
                          "enabled": false
                        }
                      },
                      "physics": {
                        "enabled": false
                      },
                      "edges": {
                        "smooth": {
                          "type": "continuous",
                          "roundness": 0.5
                        },
                        "color": {
                          "color": "#b0b0b0",
                          "highlight": "#4A90E2"
                        }
                      }
                    }
                    """)
                
                # Add nodes with logos
                for node in filtered_G.nodes():
                    node_data = node_dict.get(node, {})
                    node_type = node_data.get("type", "Unknown")
                    degree = filtered_G.degree(node)
                    
                    # Get all relationships with details
                    outgoing_rels = []
                    incoming_rels = []
                    
                    # Outgoing relationships
                    for neighbor in filtered_G.neighbors(node):
                        edge_data = filtered_G.get_edge_data(node, neighbor)
                        if edge_data:
                            rel = edge_data.get("relationship", "").replace("_", " ").title()
                            count = edge_data.get("count", 1)
                            outgoing_rels.append(f"→ <b>{neighbor}</b>: {rel}" + (f" ({count}x)" if count > 1 else ""))
                    
                    # Incoming relationships
                    for predecessor in filtered_G.predecessors(node):
                        edge_data = filtered_G.get_edge_data(predecessor, node)
                        if edge_data:
                            rel = edge_data.get("relationship", "").replace("_", " ").title()
                            count = edge_data.get("count", 1)
                            incoming_rels.append(f"← <b>{predecessor}</b>: {rel}" + (f" ({count}x)" if count > 1 else ""))
                    
                    # Build comprehensive title/tooltip
                    title = f'<div style="text-align: left; max-width: 300px;">'
                    title += f'<h3 style="margin: 5px 0; color: #2C3E50;">{node}</h3>'
                    title += f'<p style="margin: 3px 0;"><b>Type:</b> {node_type}</p>'
                    title += f'<p style="margin: 3px 0;"><b>Total Connections:</b> {degree}</p>'
                    
                    if outgoing_rels:
                        title += f'<hr style="margin: 8px 0; border: 1px solid #e0e0e0;">'
                        title += f'<p style="margin: 3px 0;"><b>Outgoing ({len(outgoing_rels)}):</b></p>'
                        title += '<ul style="margin: 3px 0; padding-left: 20px;">'
                        for rel in outgoing_rels[:8]:
                            title += f'<li style="margin: 2px 0;">{rel}</li>'
                        if len(outgoing_rels) > 8:
                            title += f'<li style="color: #888;">... and {len(outgoing_rels) - 8} more</li>'
                        title += '</ul>'
                    
                    if incoming_rels:
                        title += f'<hr style="margin: 8px 0; border: 1px solid #e0e0e0;">'
                        title += f'<p style="margin: 3px 0;"><b>Incoming ({len(incoming_rels)}):</b></p>'
                        title += '<ul style="margin: 3px 0; padding-left: 20px;">'
                        for rel in incoming_rels[:8]:
                            title += f'<li style="margin: 2px 0;">{rel}</li>'
                        if len(incoming_rels) > 8:
                            title += f'<li style="color: #888;">... and {len(incoming_rels) - 8} more</li>'
                        title += '</ul>'
                    
                    title += '</div>'
                    
                    # Size based on degree (more reasonable sizing)
                    size = max(30, min(80, 30 + degree * 3))
                    
                    # Add node with logo if it's a company
                    if node_type == "Company":
                        logo_url = get_company_logo_url(node)
                        # Use image shape for companies with thinner border
                        net.add_node(
                            node,
                            label=node,
                            title=title,
                            shape='image',
                            image=logo_url,
                            size=size,
                            color={
                                'border': get_node_color(node_type),
                                'background': '#ffffff',
                                'highlight': {'border': '#FF6B6B', 'background': '#ffffff'}
                            },
                            borderWidth=2,  # Thinner border
                            font={'size': 11, 'face': 'Arial', 'color': '#2C3E50', 'bold': True}
                        )
                    else:
                        # Use colored circle for non-companies
                        net.add_node(
                            node,
                            label=node,
                            title=title,
                            shape='dot',
                            size=size,
                            color={
                                'background': get_node_color(node_type),
                                'border': '#ffffff',
                                'highlight': {'background': get_node_color(node_type), 'border': '#FF6B6B'}
                            },
                            font={'size': 11, 'face': 'Arial', 'color': 'white', 'bold': True},
                            borderWidth=2
                        )
                
                # Add edges with thinner, more aesthetic styling
                for edge in filtered_G.edges(data=True):
                    source, target, data = edge
                    rel = data.get("relationship", "").replace("_", " ").title()
                    count = data.get("count", 1)
                    
                    # Thinner edges - cap the width
                    edge_width = min(2, max(0.5, (edge_width_factor * count) / 3))  # Much thinner
                    
                    # Enhanced edge tooltip
                    edge_title = f'<div style="text-align: left;">'
                    edge_title += f'<b>{rel}</b><br>'
                    edge_title += f'From: <b>{source}</b><br>'
                    edge_title += f'To: <b>{target}</b>'
                    if count > 1:
                        edge_title += f'<br><span style="color: #888;">Appears {count} times</span>'
                    edge_title += '</div>'
                    
                    net.add_edge(
                        source,
                        target,
                        title=edge_title,
                        width=edge_width,  # Much thinner edges
                        color={
                            'color': '#c0c0c0',  # Lighter gray
                            'highlight': '#4A90E2',
                            'hover': '#6BB6FF',
                            'opacity': 0.6  # More transparent
                        },
                        smooth={'type': 'continuous', 'roundness': 0.5},
                        arrows={'to': {'enabled': True, 'scaleFactor': 0.6}}  # Smaller arrows
                    )
                
                # Generate HTML
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w') as tmp_file:
                    net.save_graph(tmp_file.name)
                    html_file = tmp_file.name
                
                # Read and display HTML
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Make it responsive
                html_content = html_content.replace(
                    '<body>',
                    '<body style="margin: 0; padding: 0;">'
                )
                html_content = html_content.replace(
                    'width: 100%',
                    'width: 100%; height: 700px;'
                )
                
                st.components.v1.html(html_content, height=720, scrolling=False)
                
                # Clean up
                try:
                    os.unlink(html_file)
                except:
                    pass
            else:
                # Original Plotly visualization
                # Calculate layout
                if layout_type == "Spring":
                    pos = nx.spring_layout(filtered_G, k=3, iterations=50, seed=42)
                elif layout_type == "Circular":
                    pos = nx.circular_layout(filtered_G)
                elif layout_type == "Force-Directed":
                    pos = nx.spring_layout(filtered_G, k=2, iterations=100, seed=42)
                else:  # Hierarchical
                    try:
                        pos = nx.spring_layout(filtered_G, k=4, iterations=50, seed=42)
                    except:
                        pos = nx.spring_layout(filtered_G, k=2, iterations=50, seed=42)
                
                # Prepare data for Plotly
                edge_x = []
                edge_y = []
                
                for edge in filtered_G.edges(data=True):
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                # Create edge trace
                edge_trace = go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=edge_width_factor, color='rgba(125, 125, 125, 0.5)'),
                    hoverinfo='none',
                    mode='lines',
                    showlegend=False
                )
                
                # Prepare node data
                node_x = []
                node_y = []
                node_text = []
                node_info = []
                node_colors = []
                node_sizes = []
                
                for node in filtered_G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    
                    node_data = node_dict.get(node, {})
                    node_type = node_data.get("type", "Unknown")
                    degree = filtered_G.degree(node)
                    
                    # Node label with info
                    info_text = f"<b>{node}</b><br>"
                    info_text += f"Type: {node_type}<br>"
                    info_text += f"Connections: {degree}<br>"
                    
                    # Get relationships
                    relationships = []
                    for neighbor in filtered_G.neighbors(node):
                        edge_data = filtered_G.get_edge_data(node, neighbor)
                        if edge_data:
                            rel = edge_data.get("relationship", "")
                            if rel:
                                relationships.append(f"→ {neighbor}: {rel}")
                    
                    if relationships:
                        info_text += "<br>Relationships:<br>" + "<br>".join(relationships[:5])
                        if len(relationships) > 5:
                            info_text += f"<br>... and {len(relationships) - 5} more"
                    
                    node_text.append(node)
                    node_info.append(info_text)
                    node_colors.append(get_node_color(node_type))
                    node_sizes.append(max(15, degree * node_size_factor))
                
                # Create node trace
                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode='markers+text',
                    hoverinfo='text',
                    text=node_text,
                    textposition="middle center",
                    textfont=dict(size=10, color='white', family='Arial Black'),
                    hovertext=node_info,
                    marker=dict(
                        size=node_sizes,
                        color=node_colors,
                        line=dict(width=2, color='white'),
                        opacity=0.9
                    ),
                    showlegend=False
                )
                
                # Create figure
                fig = go.Figure(
                    data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=dict(
                            text=f'<b>Knowledge Graph</b> ({filtered_G.number_of_nodes()} entities, {filtered_G.number_of_edges()} relationships)',
                            x=0.5,
                            xanchor='center',
                            font=dict(size=20, color='#2C3E50')
                        ),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=60),
                        annotations=[
                            dict(
                                text="💡 Hover over nodes to see details, drag to explore",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.5, y=-0.1,
                                xanchor='center', yanchor='top',
                                font=dict(size=12, color='#7F8C8D')
                            )
                        ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        plot_bgcolor='rgba(250, 250, 250, 1)',
                        paper_bgcolor='white',
                        height=700
                    )
                )
                
                # Display interactive graph
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
            
            # Entity cards with logos
            st.subheader("🏢 Entity Details")
            entity_cols = st.columns(min(4, len(filtered_G.nodes())))
            
            for idx, node in enumerate(list(filtered_G.nodes())[:12]):  # Show first 12
                with entity_cols[idx % 4]:
                    node_data = node_dict.get(node, {})
                    node_type = node_data.get("type", "Unknown")
                    degree = filtered_G.degree(node)
                    
                    # Try to show logo for companies
                    if node_type == "Company":
                        logo_url = get_company_logo_url(node)
                        try:
                            st.image(logo_url, width=60, use_container_width=False)
                        except:
                            st.markdown(f"### {node}")
                    else:
                        st.markdown(f"### 👤 {node}")
                    
                    st.caption(f"**{node_type}** · {degree} connections")
                    
                    # Show top relationships
                    relationships = []
                    for neighbor in list(filtered_G.neighbors(node))[:3]:
                        edge_data = filtered_G.get_edge_data(node, neighbor)
                        if edge_data:
                            # For DiGraph, get_edge_data returns the edge attributes dict directly
                            rel = edge_data.get("relationship", "").replace("_", " ").title()
                            if rel:
                                relationships.append(f"{rel} → {neighbor}")
                    
                    if relationships:
                        for rel in relationships:
                            st.caption(f"• {rel}")
        
        # Show detailed information
        with st.expander("📊 Detailed Graph Statistics"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("All Entities")
                node_df_data = []
                for node in nodes:
                    node_df_data.append({
                        "Entity": node["id"],
                        "Type": node.get("type", "Unknown"),
                        "Degree": node.get("degree", 0)
                    })
                if node_df_data:
                    df_nodes = pd.DataFrame(node_df_data)
                    st.dataframe(df_nodes.sort_values("Degree", ascending=False), use_container_width=True)
            
            with col2:
                st.subheader("Relationship Types")
                relationship_counts = {}
                for edge in edges:
                    rel = edge.get("relationship", "unknown").replace("_", " ").title()
                    relationship_counts[rel] = relationship_counts.get(rel, 0) + edge.get("count", 1)
                
                df_rels = pd.DataFrame([
                    {"Relationship": rel, "Count": count}
                    for rel, count in sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(df_rels, use_container_width=True)
    else:
        st.info("No graph data available. Make sure extractions have been processed.")


with tab_analytics:
    st.header("📈 Analytics Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top PageRank Entities")
        st.caption("Entities ranked by influence in the graph")
        top_k = st.slider("Top K", min_value=5, max_value=50, value=10, key="pagerank_k")
        pagerank = _fetch_json("/api/graph/analytics/pagerank", params={"top_k": top_k})
        
        if pagerank.get("top_entities"):
            # Create a bar chart
            import pandas as pd
            df_pr = pd.DataFrame(pagerank.get("top_entities", []))
            if not df_pr.empty:
                st.bar_chart(df_pr.set_index("entity")["score"])
            
            # Show list
            for rank, entry in enumerate(pagerank.get("top_entities", []), start=1):
                st.write(f"{rank}. **{entry['entity']}** — {entry['score']:.4f}")
        else:
            st.info("No PageRank data available.")

    with col2:
        st.subheader("Relationship Trends")
        relationship = st.text_input("Relationship type", value="collaborates_with", key="trend_rel")
        granularity = st.selectbox("Granularity", ["day", "week", "month"], index=1, key="trend_gran")
        
        trends = _fetch_json(
            "/api/graph/analytics/trends",
            params={"relationship": relationship, "granularity": granularity},
        )
        series = trends.get("series", [])
        if series:
            st.line_chart(
                {
                    "bucket": [row["bucket"] for row in series],
                    "count": [row["count"] for row in series],
                },
                x="bucket",
                y="count",
            )
        else:
            st.info("No trend data available.")
    
    # Communities
    st.subheader("🔗 Detected Communities")
    min_size = st.slider("Minimum Community Size", min_value=2, max_value=10, value=3, key="comm_size")
    communities = _fetch_json("/api/graph/analytics/communities", params={"min_size": min_size})
    
    if communities.get("communities"):
        for i, comm in enumerate(communities.get("communities", []), 1):
            with st.expander(f"Community {comm.get('community_id', i)} ({len(comm.get('members', []))} members)"):
                st.write(", ".join(comm.get("members", [])))
    else:
        st.info("No communities detected. Try adjusting the minimum size.")
