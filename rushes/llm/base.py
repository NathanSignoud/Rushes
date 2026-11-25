"""Interface commune des fournisseurs LLM (SPEC §9).

Les sous-classes n'implémentent que `_generate` (envoyer les messages, rendre le texte et les
tokens). Validation pydantic, réparation, budget, débit et journal sont faits ici, une fois.
"""

import json
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from rushes.config import charger_prompt
from rushes.llm.budget import Budget
from rushes.llm.ratelimit import RateLimiter
from rushes.storage import Storage

M = TypeVar("M", bound=BaseModel)
Messages = list[dict[str, str]]


class LLMError(Exception):
    pass


def extraire_json(texte: str) -> str:
    """Les modèles entourent parfois le JSON de texte ou de ```json … ```."""
    debut, fin = texte.find("{"), texte.rfind("}")
    return texte[debut : fin + 1] if debut != -1 and fin > debut else texte


class LLMProvider:
    def __init__(
        self,
        *,
        budget: Budget | None = None,
        limiter: RateLimiter | None = None,
        journal: Storage | None = None,
        debug_prompts: bool = False,
    ):
        self.budget = budget
        self.limiter = limiter
        self.journal = journal
        self.debug_prompts = debug_prompts

    def _generate(
        self, messages: Messages, schema: type[BaseModel], temperature: float
    ) -> tuple[str, int]:
        """Renvoie (texte de la réponse, tokens consommés)."""
        raise NotImplementedError

    def complete_json(
        self,
        prompt: str,
        schema: type[M],
        *,
        system: str | None = None,
        temperature: float = 0.8,
        tag: str = "",
    ) -> M:
        messages: Messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        for _ in range(2):  # 1 essai + 1 réparation
            resultat, texte, erreur = self._appel(messages, schema, temperature, tag)
            if resultat is not None:
                return resultat
            reparation = charger_prompt("reparation_json").format(erreur=erreur)
            messages = [
                *messages,
                {"role": "assistant", "content": texte},
                {"role": "user", "content": reparation},
            ]
        raise LLMError(f"Réponse invalide pour « {tag} » malgré une réparation : {erreur}")

    def _appel(
        self, messages: Messages, schema: type[M], temperature: float, tag: str
    ) -> tuple[M | None, str, ValidationError | None]:
        if self.budget:
            self.budget.verifier()
        if self.limiter:
            self.limiter.attendre()
        debut = time.perf_counter()
        texte, tokens, resultat, erreur = "", 0, None, None
        try:
            texte, tokens = self._generate(messages, schema, temperature)
            resultat = schema.model_validate_json(extraire_json(texte))
        except ValidationError as e:
            erreur = e
        finally:  # journalise aussi les erreurs réseau, qui remontent ensuite
            if self.budget:
                self.budget.enregistrer(tokens)
            if self.journal:
                self.journal.log_llm_call(
                    tag,
                    int((time.perf_counter() - debut) * 1000),
                    tokens,
                    resultat is not None,
                    json.dumps(messages, ensure_ascii=False) if self.debug_prompts else None,
                    texte if self.debug_prompts else None,
                )
        return resultat, texte, erreur
