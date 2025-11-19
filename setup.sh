#!/bin/bash

# Nexus Project Setup Script
# Run this to initialize the project

echo "======================================"
echo "🔷 Nexus Project Setup"
echo "======================================"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✨ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Download NLTK data
echo "📚 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p data
mkdir -p data/extractions
mkdir -p mock_data
mkdir -p config/prompts
mkdir -p tests

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys"
fi

# Generate mock data
echo "🎲 Generating mock data..."
python -m ingestion.mock_generator

# Initialize empty __init__.py files
echo "📄 Creating module files..."
touch ingestion/__init__.py
touch search/__init__.py
touch extraction/__init__.py
touch graph/__init__.py

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys (optional)"
echo "2. Run data ingestion:"
echo "   python -m ingestion.news_fetcher"
echo ""
echo "3. Build search index:"
echo "   python -m search.indexer"
echo ""
echo "4. Extract relationships (use --mock for testing):"
echo "   python -m extraction.batch_process --mock"
echo ""
echo "5. Start the API server:"
echo "   python main.py"
echo ""
echo "6. Launch the UI (in a new terminal):"
echo "   streamlit run streamlit_demo.py"
echo ""
echo "======================================"