#!/usr/bin/env python3
"""Test script for hybrid BM25 + Embedding search system."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all modules can be imported."""
    print("=" * 60)
    print("Testing Imports")
    print("=" * 60)
    
    try:
        from module2_search.bm25 import BM25Index
        print("✅ BM25Index imported successfully")
    except Exception as e:
        print(f"❌ Failed to import BM25Index: {e}")
        return False
    
    try:
        from module2_search.embeddings import EmbeddingIndex
        print("✅ EmbeddingIndex imported successfully")
    except ImportError as e:
        print(f"⚠️  EmbeddingIndex not available (sentence-transformers may not be installed): {e}")
        print("   This is OK - system will fall back to BM25-only mode")
    except Exception as e:
        print(f"❌ Failed to import EmbeddingIndex: {e}")
        return False
    
    try:
        from module2_search.indexer import ArticleIndexer
        print("✅ ArticleIndexer imported successfully")
    except Exception as e:
        print(f"❌ Failed to import ArticleIndexer: {e}")
        return False
    
    try:
        from module2_search.preprocessor import TextPreprocessor
        print("✅ TextPreprocessor imported successfully")
    except Exception as e:
        print(f"❌ Failed to import TextPreprocessor: {e}")
        return False
    
    print()
    return True


def test_bm25_index():
    """Test BM25Index functionality."""
    print("=" * 60)
    print("Testing BM25Index")
    print("=" * 60)
    
    try:
        from module2_search.bm25 import BM25Index
        
        # Create index
        bm25 = BM25Index(k1=1.5, b=0.75)
        
        # Add test documents
        test_docs = [
            ("doc1", ["financial", "market", "analysis"]),
            ("doc2", ["stock", "price", "financial"]),
            ("doc3", ["market", "trend", "analysis"]),
        ]
        
        for doc_id, tokens in test_docs:
            bm25.add_document(doc_id, tokens)
        
        bm25.finalize()
        
        print(f"✅ Added {len(test_docs)} documents")
        print(f"   Average doc length: {bm25.avg_doc_length:.2f}")
        print(f"   Vocabulary size: {len(bm25.inverted_index)}")
        
        # Test search
        query_tokens = ["financial", "market"]
        results = bm25.score(query_tokens, k=3)
        
        print(f"✅ Search query '{' '.join(query_tokens)}' returned {len(results)} results")
        for doc_id, score in results:
            print(f"   - {doc_id}: {score:.4f}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ BM25Index test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_embedding_index():
    """Test EmbeddingIndex functionality."""
    print("=" * 60)
    print("Testing EmbeddingIndex")
    print("=" * 60)
    
    try:
        from module2_search.embeddings import EmbeddingIndex
        
        # Create index
        emb_index = EmbeddingIndex(model_name="all-mpnet-base-v2")
        
        # Add test documents
        test_docs = [
            ("doc1", "Financial market analysis shows positive trends"),
            ("doc2", "Stock prices are rising in the financial sector"),
            ("doc3", "Market trends indicate strong performance"),
        ]
        
        emb_index.build(test_docs)
        
        print(f"✅ Built embedding index with {len(test_docs)} documents")
        print(f"   Embedding matrix shape: {emb_index._emb_matrix.shape if emb_index._emb_matrix is not None else 'None'}")
        
        # Test search
        query = "financial markets"
        results = emb_index.search(query, k=3)
        
        print(f"✅ Search query '{query}' returned {len(results)} results")
        for doc_id, score in results:
            print(f"   - {doc_id}: {score:.4f}")
        
        print()
        return True
        
    except ImportError as e:
        print(f"⚠️  EmbeddingIndex not available: {e}")
        print("   Install with: pip install sentence-transformers")
        print("   System will work in BM25-only mode")
        print()
        return None  # Not a failure, just not available
    except Exception as e:
        print(f"❌ EmbeddingIndex test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_article_indexer():
    """Test ArticleIndexer with hybrid search."""
    print("=" * 60)
    print("Testing ArticleIndexer (Hybrid Search)")
    print("=" * 60)
    
    try:
        from module2_search.indexer import ArticleIndexer
        from module2_search.preprocessor import TextPreprocessor
        
        # Create a small test dataset
        import json
        import tempfile
        
        test_articles = [
            {
                "article_id": "test_001",
                "headline": "Financial Markets Show Strong Performance",
                "full_text": "Financial markets have shown exceptional performance this quarter. Stock prices are rising across multiple sectors.",
                "source": "Test Source",
                "publication_date": "2024-01-01",
                "processed": False
            },
            {
                "article_id": "test_002",
                "headline": "Stock Market Analysis Reveals Positive Trends",
                "full_text": "Recent analysis of stock market data indicates positive trends in technology and finance sectors.",
                "source": "Test Source",
                "publication_date": "2024-01-02",
                "processed": False
            },
            {
                "article_id": "test_003",
                "headline": "Economic Indicators Point to Growth",
                "full_text": "Economic indicators suggest strong growth in the coming months. Investors are optimistic.",
                "source": "Test Source",
                "publication_date": "2024-01-03",
                "processed": False
            }
        ]
        
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_articles, f)
            temp_path = f.name
        
        try:
            # Create indexer
            indexer = ArticleIndexer(
                articles_path=temp_path,
                embed_alpha=0.6  # 60% weight on embeddings, 40% on BM25
            )
            
            # Build index
            print("Building hybrid index...")
            indexer.build_index()
            
            # Get stats
            stats = indexer.stats()
            print(f"✅ Index built successfully")
            print(f"   Documents: {stats['documents']}")
            print(f"   Avg doc length: {stats['avg_doc_length']:.2f}")
            print(f"   Vocabulary size: {stats['vocabulary_size']}")
            print(f"   Has embeddings: {stats['has_embeddings']}")
            
            # Test search
            query = "financial markets stock"
            print(f"\n🔍 Testing search: '{query}'")
            results = indexer.search(query, k=3)
            
            print(f"✅ Search returned {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"\n   Result {i}:")
                print(f"   - Article ID: {result['article_id']}")
                print(f"   - Headline: {result['headline']}")
                print(f"   - BM25 Score: {result['bm25_score']}")
                print(f"   - Embed Score: {result['embed_score']}")
                print(f"   - Combined Score: {result['combined_score']}")
            
            print()
            return True
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"❌ ArticleIndexer test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Hybrid Search System Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test BM25
    results.append(("BM25Index", test_bm25_index()))
    
    # Test Embeddings (may be None if not available)
    emb_result = test_embedding_index()
    results.append(("EmbeddingIndex", emb_result))
    
    # Test ArticleIndexer
    results.append(("ArticleIndexer", test_article_indexer()))
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"✅ {name}: PASSED")
            passed += 1
        elif result is False:
            print(f"❌ {name}: FAILED")
            failed += 1
        else:  # None
            print(f"⚠️  {name}: SKIPPED (not available)")
            skipped += 1
    
    print()
    print(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    print()
    
    if failed == 0:
        print("✅ All available tests passed!")
        if skipped > 0:
            print("   (Some features skipped - install sentence-transformers for full functionality)")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

