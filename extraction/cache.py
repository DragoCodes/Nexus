"""
Disk-backed cache for extraction outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class ExtractionCache:
    def __init__(self, cache_dir: str = "data/extractions"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, article_id: str) -> Path:
        return self.cache_dir / f"{article_id}.json"

    def exists(self, article_id: str) -> bool:
        return self._path(article_id).exists()

    def load(self, article_id: str) -> Optional[Dict]:
        path = self._path(article_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, article_id: str, payload: Dict) -> Path:
        path = self._path(article_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return path

    def list_cached(self) -> List[str]:
        return sorted(p.stem for p in self.cache_dir.glob("*.json"))
