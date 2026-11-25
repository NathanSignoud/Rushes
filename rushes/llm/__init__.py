"""Seul point d'accès aux LLM du projet (SPEC §9)."""

import os
from pathlib import Path

import openai
from dotenv import load_dotenv

from rushes.config import Config
from rushes.llm.base import LLMError, LLMProvider
from rushes.llm.budget import Budget
from rushes.llm.mock import MockProvider
from rushes.llm.openai_compat import OpenAICompatProvider
from rushes.llm.ratelimit import RateLimiter
from rushes.storage import Storage


def creer_llm(
    config: Config, journal: Storage, seed: int, provider: str | None = None
) -> LLMProvider:
    nom = provider or config.llm.provider
    commun = dict(
        budget=Budget(config.budget.max_appels),
        journal=journal,
        debug_prompts=config.llm.debug_prompts,
    )
    if nom == "mock":
        return MockProvider(seed=seed, **commun)
    load_dotenv(Path(".env"))
    fournisseur = getattr(config.llm, nom)
    cle = os.environ.get(fournisseur.api_key_env)
    if not cle:  # ne jamais afficher la clé elle-même
        raise LLMError(f"Clé API absente : renseigne {fournisseur.api_key_env} dans .env")
    client = openai.OpenAI(base_url=fournisseur.base_url, api_key=cle, max_retries=5)
    limiter = RateLimiter(config.llm.max_requetes_par_minute)
    return OpenAICompatProvider(client, fournisseur.model, limiter=limiter, **commun)
