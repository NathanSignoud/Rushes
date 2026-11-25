"""Fournisseur factice : réponses valides et déterministes (seedées) pour n'importe quel schéma.

Il parcourt le JSON Schema du modèle pydantic demandé et remplit chaque champ en respectant
types, bornes, énumérations et `examples` (utilisés pour les champs à motif, ex. une heure).
"""

import json
import random
from typing import Any

from pydantic import BaseModel

from rushes.llm.base import LLMProvider, Messages


class MockProvider(LLMProvider):
    def __init__(self, seed: int = 0, **kwargs: Any):
        super().__init__(**kwargs)
        self.rng = random.Random(seed)

    def _generate(
        self, messages: Messages, schema: type[BaseModel], temperature: float
    ) -> tuple[str, int]:
        js = schema.model_json_schema()
        texte = json.dumps(self._valeur(js, js.get("$defs", {}), "texte"), ensure_ascii=False)
        tokens = (sum(len(m["content"]) for m in messages) + len(texte)) // 4  # ~4 car./token
        return texte, tokens

    def _valeur(self, node: dict, defs: dict, nom: str) -> Any:
        if "$ref" in node:
            return self._valeur(defs[node["$ref"].rsplit("/", 1)[-1]], defs, nom)
        if "examples" in node:
            return self.rng.choice(node["examples"])
        if "const" in node:
            return node["const"]
        if "enum" in node:
            return self.rng.choice(node["enum"])
        if "anyOf" in node:
            non_nuls = [o for o in node["anyOf"] if o.get("type") != "null"]
            return self._valeur(self.rng.choice(non_nuls), defs, nom)
        match node.get("type"):
            case "object":
                props = node.get("properties", {})
                return {k: self._valeur(v, defs, k) for k, v in props.items()}
            case "array":
                items = node.get("items", {})
                return [self._valeur(items, defs, nom) for _ in range(self.rng.randint(1, 2))]
            case "integer":
                bas = node.get("minimum", 0)
                return self.rng.randint(bas, node.get("maximum", bas + 10))
            case "number":
                bas = node.get("minimum", 0.0)
                return round(self.rng.uniform(bas, node.get("maximum", bas + 1.0)), 3)
            case "boolean":
                return self.rng.random() < 0.5
            case "string":
                return f"{nom} {self.rng.randint(1, 999)}"
        return None
