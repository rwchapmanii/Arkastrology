from typing import Dict, List

from app.services.content_loader import load_ontology


class CitationService:
    @staticmethod
    def get_all() -> List[Dict]:
        return load_ontology()["citations"]

    @staticmethod
    def resolve(ids: List[str]) -> List[Dict]:
        citations = load_ontology()["citations"]
        by_id = {item["id"]: item for item in citations}
        return [by_id[citation_id] for citation_id in ids if citation_id in by_id]
