import json
from pathlib import Path

from extraction.cache import ExtractionCache
from extraction.llm_client import LLMClient
from extraction.parser import parse_llm_response


def test_parse_llm_response_validates():
    payload = json.dumps(
        [
            {
                "entity1": "NVIDIA",
                "entity1_type": "Company",
                "relationship": "partners_with",
                "entity2": "TSMC",
                "entity2_type": "Company",
                "confidence": 0.95,
            }
        ]
    )
    result = parse_llm_response(
        article_id="abc",
        raw_response=payload,
        metadata={"headline": "Test"},
    )
    assert result["article_id"] == "abc"
    assert result["triples"][0]["relationship"] == "partners_with"


def test_cache_roundtrip(tmp_path: Path):
    cache = ExtractionCache(cache_dir=tmp_path)
    payload = {"article_id": "a1", "triples": [], "extracted_at": "now"}
    cache.save("a1", payload)
    loaded = cache.load("a1")
    assert loaded == payload
    assert cache.exists("a1")


def test_llm_client_mock_lookup():
    mock_data = [
        {
            "article_id": "mock-1",
            "triples": [
                {
                    "entity1": "Meta",
                    "entity1_type": "Company",
                    "relationship": "acquires",
                    "entity2": "StartUp",
                    "entity2_type": "Company",
                    "confidence": 0.8,
                }
            ],
        }
    ]
    client = LLMClient(mock_responses=mock_data)
    output = client.generate("mock-1", "Meta acquires StartUp.")
    triples = json.loads(output)
    assert triples[0]["entity1"] == "Meta"
