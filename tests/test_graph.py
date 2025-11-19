from graph.analytics import compute_pagerank
from graph.builder import KnowledgeGraphBuilder
from graph.queries import shortest_path


def _sample_builder() -> KnowledgeGraphBuilder:
    builder = KnowledgeGraphBuilder()
    builder.add_extraction_result(
        {
            "article_id": "1",
            "triples": [
                {
                    "entity1": "NVIDIA",
                    "entity1_type": "Company",
                    "relationship": "partners_with",
                    "entity2": "TSMC",
                    "entity2_type": "Company",
                    "confidence": 0.9,
                },
                {
                    "entity1": "TSMC",
                    "entity1_type": "Company",
                    "relationship": "supplies_to",
                    "entity2": "Apple",
                    "entity2_type": "Company",
                    "confidence": 0.85,
                },
            ],
            "metadata": {"publication_date": "2024-03-01T00:00:00Z"},
        }
    )
    return builder


def test_graph_builder_stats():
    builder = _sample_builder()
    stats = builder.get_statistics()
    assert stats["nodes"] == 3
    assert stats["edges"] == 2


def test_pagerank_scores():
    builder = _sample_builder()
    scores = compute_pagerank(builder.graph, top_k=2)
    assert scores
    assert scores[0]["score"] >= scores[1]["score"]


def test_shortest_path():
    builder = _sample_builder()
    path = shortest_path(builder.graph, "NVIDIA", "Apple")
    assert path == ["NVIDIA", "TSMC", "Apple"]
