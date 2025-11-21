#!/usr/bin/env python3
"""Check if Nexus setup is complete and ready to run."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_file_exists(path, name):
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✅ {name}: Found")
        return True
    else:
        print(f"❌ {name}: Not found at {path}")
        return False

def check_env_var(var_name):
    """Check if environment variable is set."""
    value = os.getenv(var_name)
    if value:
        print(f"✅ {var_name}: Set")
        return True
    else:
        print(f"❌ {var_name}: Not set")
        return False

def main():
    """Check setup status."""
    print("=" * 60)
    print("Nexus Setup Verification")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent
    all_ok = True
    
    # Check environment variables
    print("📋 Environment Variables:")
    print("-" * 60)
    all_ok &= check_env_var("NEWS_API_KEY")
    all_ok &= check_env_var("GEMINI_API_KEY")
    all_ok &= check_env_var("MONGODB_URI")
    
    # MongoDB DB name and collection have defaults, so optional
    mongodb_db = os.getenv("MONGODB_DB_NAME", "nexus_db")
    mongodb_collection = os.getenv("MONGODB_COLLECTION_NAME", "articles")
    print(f"ℹ️  MONGODB_DB_NAME: {mongodb_db} (default)")
    print(f"ℹ️  MONGODB_COLLECTION_NAME: {mongodb_collection} (default)")
    print()
    
    # Check required files
    print("📁 Required Files:")
    print("-" * 60)
    all_ok &= check_file_exists(
        project_root / "data" / "index" / "inverted_index.pkl",
        "Search Index"
    )
    all_ok &= check_file_exists(
        project_root / "data" / "nexus_graph.db",
        "Graph Database"
    )
    print()
    
    # Check optional but recommended files
    print("📁 Optional Files (for full functionality):")
    print("-" * 60)
    check_file_exists(
        project_root / ".env",
        ".env file"
    )
    check_file_exists(
        project_root / "data" / "exports" / "pagerank_results.json",
        "PageRank Results (optional)"
    )
    print()
    
    # Check Python packages
    print("📦 Python Packages:")
    print("-" * 60)
    required_packages = [
        "streamlit",
        "pymongo",
        "networkx",
        "pyvis",
        "plotly",
        "pandas",
        "nltk",
        "google.generativeai"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == "google.generativeai":
                __import__("google.generativeai")
            else:
                __import__(package)
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Not installed")
            missing_packages.append(package)
            all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok and not missing_packages:
        print("✅ Setup Complete! You can run the frontend:")
        print()
        print("   streamlit run frontend/app.py")
        print()
        print("   Or use: python run_frontend.py")
    else:
        print("⚠️  Setup Incomplete. Please fix the issues above.")
        print()
        if missing_packages:
            print("To install missing packages:")
            print("   uv sync")
            print("   # Or: pip install -r requirements.txt")
        print()
        print("See README.md or QUICKSTART.md for detailed instructions.")
    
    print("=" * 60)
    
    return 0 if all_ok and not missing_packages else 1

if __name__ == "__main__":
    sys.exit(main())

