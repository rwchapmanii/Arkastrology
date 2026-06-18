import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[4]
ONTOLOGY_DIR = BASE_DIR / "content" / "ontology"


def _load_json(filename: str) -> List[Dict[str, Any]]:
    with (ONTOLOGY_DIR / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_ontology() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "planets": _load_json("planets.json"),
        "signs": _load_json("signs.json"),
        "houses": _load_json("houses.json"),
        "aspects": _load_json("aspects.json"),
        "jungian_mappings": _load_json("jungian-mappings.json"),
        "levi_currents": _load_json("levi-currents.json"),
        "planetary_rites": _load_json("planetary-rites.json"),
        "transit_thresholds": _load_json("transit-thresholds.json"),
        "citations": _load_json("citations.json"),
        "doctrine_layers": _load_json("doctrine-layers.json"),
    }
