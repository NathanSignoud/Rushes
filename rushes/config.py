"""Chargement de ce que l'utilisateur édite sur disque : config.yaml, casting/, prompts/."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from rushes.models import Habitant, Monde

RACINE = Path(__file__).resolve().parent.parent
PROMPTS_DIR = RACINE / "prompts"
# Relatifs au dossier courant : on lance `python -m rushes` depuis la racine du projet.
CONFIG_PATH = Path("config.yaml")
CASTING_DIR = Path("casting")
DATA_DIR = Path("data")
DB_NAME = "rushes.sqlite"


# Les sections sim/memoire/dialogue/show/producteur/web seront typées dans leur phase.
class FournisseurConfig(BaseModel):
    base_url: str
    model: str
    api_key_env: str


class TemperatureConfig(BaseModel):
    habitant: float
    ecriture: float
    fact_checker: float


class LLMConfig(BaseModel):
    provider: Literal["mock", "gemini", "groq"]
    gemini: FournisseurConfig
    groq: FournisseurConfig
    max_requetes_par_minute: int = Field(gt=0)
    temperature: TemperatureConfig
    cache: bool = False
    debug_prompts: bool = False


class BudgetConfig(BaseModel):
    max_appels: int = Field(gt=0)


class Config(BaseModel):
    seed: int
    llm: LLMConfig
    budget: BudgetConfig


def charger_config(path: Path = CONFIG_PATH) -> Config:
    return Config.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def charger_prompt(nom: str) -> str:
    return (PROMPTS_DIR / f"{nom}.md").read_text(encoding="utf-8")


def charger_casting(dossier: Path = CASTING_DIR) -> tuple[Monde, list[Habitant]]:
    """Charge et valide le casting, y compris les références croisées entre fiches."""
    monde = Monde.model_validate_json((dossier / "world.json").read_text(encoding="utf-8"))
    habitants = [
        Habitant.model_validate_json(f.read_text(encoding="utf-8"))
        for f in sorted((dossier / "habitants").glob("*.json"))
    ]
    erreurs = _verifier_references(monde, habitants)
    if erreurs:
        raise ValueError("Casting invalide :\n- " + "\n- ".join(erreurs))
    return monde, habitants


def _verifier_references(monde: Monde, habitants: list[Habitant]) -> list[str]:
    lieux = [lieu.id for lieu in monde.lieux]
    ids = [h.id for h in habitants]
    erreurs = [f"id en double : {x}" for x in {*lieux, *ids} if (lieux + ids).count(x) > 1]
    for lieu in monde.lieux:
        if lieu.proprietaire and lieu.proprietaire not in ids:
            erreurs.append(f"{lieu.id} : propriétaire inconnu {lieu.proprietaire}")
        erreurs += [f"{lieu.id} : voisin inconnu {v}" for v in lieu.voisins if v not in lieux]
    for h in habitants:
        for champ in ("domicile", "lieu_travail"):
            valeur = getattr(h, champ)
            if valeur and valeur not in lieux:
                erreurs.append(f"{h.id} : {champ} inconnu {valeur}")
        erreurs += [
            f"{h.id} : relation vers un inconnu {r}"
            for r in h.relations
            if r not in ids or r == h.id
        ]
        erreurs += [
            f"{h.id} : secret {s.id} connu d'un inconnu {c}"
            for s in h.secrets
            for c in s.connu_de
            if c not in ids
        ]
    return erreurs
