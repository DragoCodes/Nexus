"""
Nexus - Main Application
Integrated Flask API combining all modules
"""
from flask import Flask, jsonify, render_template_string
from search.api import search_blueprint
from graph.api import graph_blueprint
import os

app = Flask(__name__)

# Register blueprints
app.register_blueprint(search_blueprint, url_prefix='/api/search')
app.register_blueprint(graph_blueprint, url_prefix='/api/graph')


@app.route('/')
def index():
    """Landing page with API documentation"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nexus - Financial Intelligence Knowledge Graph</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
            }
            .section {
                background: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #667eea;
                margin: 10px 0;
                border-radius: 4px;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 10px;
            }
            .get { background: #28a745; color: white; }
            .post { background: #007bff; color: white; }
            code {
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            .status {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
                margin-left: 10px;
            }
            .running { background: #28a745; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔷 Nexus API</h1>
            <p>Financial Intelligence Knowledge Graph</p>
            <span class="status running">● Running</span>
        </div>
        
        <div class="section">
            <h2>📖 Quick Start</h2>
            <p>Nexus transforms financial news into a queryable knowledge graph. Use the API endpoints below to search articles, explore entity relationships, and analyze market trends.</p>
        </div>
        
        <div class="section">
            <h2>🔍 Search API</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/search/search?q=&lt;query&gt;&k=&lt;int&gt;</code>
                <p>Search articles using BM25 ranking</p>
                <strong>Example:</strong> <code>/api/search/search?q=NVIDIA%20AI&k=10</code>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/search/article/&lt;article_id&gt;</code>
                <p>Get full article by ID</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/search/stats</code>
                <p>Get search index statistics</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🕸️ Graph API</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/graph/entity/&lt;entity_name&gt;</code>
                <p>Get entity relationships and metadata</p>
                <strong>Example:</strong> <code>/api/graph/entity/NVIDIA</code>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/graph/analytics/pagerank?top_k=20</code>
                <p>Calculate PageRank to identify influential entities</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/graph/analytics/communities?min_size=3</code>
                <p>Detect entity communities using Louvain algorithm</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/graph/analytics/trends?relationship=&lt;type&gt;&granularity=day</code>
                <p>Analyze temporal trends in relationships</p>
                <strong>Example:</strong> <code>/api/graph/analytics/trends?relationship=partners_with&granularity=week</code>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/graph/path/&lt;source&gt;/&lt;target&gt;</code>
                <p>Find shortest path between two entities</p>
                <strong>Example:</strong> <code>/api/graph/path/NVIDIA/TSMC</code>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/graph/stats</code>
                <p>Get knowledge graph statistics</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🚀 Example Workflow</h2>
            <ol>
                <li><strong>Search for articles:</strong> <code>GET /api/search/search?q=semiconductor&k=5</code></li>
                <li><strong>Explore an entity:</strong> <code>GET /api/graph/entity/TSMC</code></li>
                <li><strong>Find influential players:</strong> <code>POST /api/graph/analytics/pagerank</code></li>
                <li><strong>Analyze trends:</strong> <code>GET /api/graph/analytics/trends?granularity=week</code></li>
            </ol>
        </div>
        
        <div class="section">
            <h2>📊 System Status</h2>
            <p><a href="/api/search/stats">Search Index Status</a> | <a href="/api/graph/stats">Graph Status</a></p>
        </div>
        
        <div class="section">
            <h2>🎨 UI Demo</h2>
            <p>For an interactive UI, run: <code>streamlit run streamlit_demo.py</code></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Nexus API',
        'version': '1.0.0'
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🔷 Nexus - Financial Intelligence Knowledge Graph")
    print("=" * 60)
    print()
    print("Starting integrated API server...")
    print()
    print("📍 API Base URL: http://localhost:5000")
    print("📖 Documentation: http://localhost:5000/")
    print()
    print("Modules loaded:")
    print("  ✓ Search Engine (BM25)")
    print("  ✓ Knowledge Graph (NetworkX)")
    print("  ✓ Analytics (PageRank, Communities, Trends)")
    print()
    print("=" * 60)
    
    app.run(
        debug=False,
        port=5000,
        host='0.0.0.0'
    )