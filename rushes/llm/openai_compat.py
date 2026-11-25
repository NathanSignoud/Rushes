"""Gemini et Groq via leurs endpoints compatibles OpenAI (SDK `openai`)."""

import openai
from pydantic import BaseModel

from rushes.llm.base import LLMProvider, Messages
from rushes.llm.budget import BudgetEpuise


class OpenAICompatProvider(LLMProvider):
    def __init__(self, client: openai.OpenAI, model: str, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.model = model

    def _generate(
        self, messages: Messages, schema: type[BaseModel], temperature: float
    ) -> tuple[str, int]:
        # Pas de response_format : le mode JSON n'est documenté que chez Groq. Le JSON est
        # extrait puis validé dans la classe de base, avec une réparation si besoin.
        try:
            r = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature
            )
        except openai.RateLimitError as e:  # le SDK a déjà réessayé (backoff exponentiel)
            raise BudgetEpuise(f"Quota du fournisseur atteint (429) : {e}") from e
        return r.choices[0].message.content or "", r.usage.total_tokens if r.usage else 0
