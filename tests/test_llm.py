import inspect
from contextlib import closing
from types import SimpleNamespace

import httpx
import openai
import pytest
from pydantic import BaseModel

from rushes import models
from rushes.config import RACINE, charger_config
from rushes.llm import creer_llm
from rushes.llm.base import LLMError, LLMProvider, extraire_json
from rushes.llm.budget import Budget, BudgetEpuise
from rushes.llm.mock import MockProvider
from rushes.llm.openai_compat import OpenAICompatProvider
from rushes.llm.ratelimit import RateLimiter
from rushes.models import Souvenir
from rushes.storage import Storage

SCHEMAS = [
    obj
    for _, obj in inspect.getmembers(models, inspect.isclass)
    if issubclass(obj, BaseModel) and obj.__module__ == models.__name__
]


@pytest.mark.parametrize("schema", SCHEMAS, ids=lambda s: s.__name__)
def test_mock_valide_et_deterministe(schema):
    a = MockProvider(seed=42).complete_json("prompt", schema)
    b = MockProvider(seed=42).complete_json("prompt", schema)
    assert isinstance(a, schema)
    assert a == b


class Script(LLMProvider):
    """Fournisseur qui rejoue des réponses écrites à l'avance."""

    def __init__(self, reponses: list, **kwargs):
        super().__init__(**kwargs)
        self.reponses = reponses
        self.recus: list = []

    def _generate(self, messages, schema, temperature):
        self.recus.append(messages)
        reponse = self.reponses.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse, 10


VALIDE = (
    '{"id": "mem_1", "habitant_id": "lea", "jour": 1, "heure": "08:00", "type": "observation",'
    ' "contenu": "x", "importance": 3, "derniere_consultation": "j1-08:00"}'
)


def test_reparation_puis_succes(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        llm = Script(['{"id": "mem_1"}', VALIDE], journal=s)
        assert llm.complete_json("p", Souvenir, tag="decision").id == "mem_1"
        # l'erreur de validation est renvoyée au modèle
        assert "habitant_id" in llm.recus[1][-1]["content"]
        assert s.llm_stats() == [("decision", 2, 20, 1, s.llm_stats()[0][4])]


def test_reparation_echoue():
    llm = Script(["pas du json", "toujours pas"])
    with pytest.raises(LLMError, match="malgré une réparation"):
        llm.complete_json("p", Souvenir, tag="decision")


def test_erreur_reseau_journalisee_puis_remontee(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        llm = Script([ConnectionError("hors ligne")], journal=s)
        with pytest.raises(ConnectionError):
            llm.complete_json("p", Souvenir, tag="decision")
        assert s.llm_stats()[0][:4] == ("decision", 1, 0, 1)


def test_budget_plafond_dur():
    budget = Budget(max_appels=2)
    llm = MockProvider(seed=1, budget=budget)
    llm.complete_json("p", Souvenir)
    llm.complete_json("p", Souvenir)
    with pytest.raises(BudgetEpuise):
        llm.complete_json("p", Souvenir)
    assert budget.appels == 2 and budget.tokens > 0


def test_extraire_json():
    assert extraire_json('Voilà :\n```json\n{"a": {"b": 1}}\n```') == '{"a": {"b": 1}}'
    assert extraire_json("pas de json") == "pas de json"


class FauxClient:
    """Imite `openai.OpenAI().chat.completions.create`."""

    def __init__(self, reponse=None, erreur=None):
        self.reponse, self.erreur, self.appels = reponse, erreur, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.appels.append(kwargs)
        if self.erreur:
            raise self.erreur
        return self.reponse


def test_openai_compat_texte_et_tokens():
    reponse = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="```json\n" + VALIDE + "\n```"))],
        usage=SimpleNamespace(total_tokens=42),
    )
    client = FauxClient(reponse)
    budget = Budget(10)
    llm = OpenAICompatProvider(client, "modele-x", budget=budget)
    assert llm.complete_json("p", Souvenir, temperature=0.3).id == "mem_1"
    assert client.appels[0]["model"] == "modele-x" and client.appels[0]["temperature"] == 0.3
    assert budget.tokens == 42


def test_openai_compat_quota_429_devient_budget_epuise():
    requete = httpx.Request("POST", "https://exemple.invalid")
    erreur = openai.RateLimitError("trop", response=httpx.Response(429, request=requete), body=None)
    llm = OpenAICompatProvider(FauxClient(erreur=erreur), "modele-x")
    with pytest.raises(BudgetEpuise, match="429"):
        llm.complete_json("p", Souvenir)


def test_creer_llm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # aucun .env ici
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    config = charger_config(RACINE / "config.yaml")
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        assert isinstance(creer_llm(config, s, seed=1), MockProvider)
        with pytest.raises(LLMError, match="GROQ_API_KEY"):
            creer_llm(config, s, seed=1, provider="groq")
        monkeypatch.setenv("GROQ_API_KEY", "cle-de-test")
        llm = creer_llm(config, s, seed=1, provider="groq")
        assert isinstance(llm, OpenAICompatProvider) and llm.model == "openai/gpt-oss-20b"
        assert llm.limiter is not None and llm.budget.max_appels == 400


def test_rate_limiter_espace_les_appels():
    temps = [0.0]
    attentes: list[float] = []

    def dormir(d: float) -> None:
        attentes.append(d)
        temps[0] += d

    limiter = RateLimiter(10, clock=lambda: temps[0], sleep=dormir)
    limiter.attendre()  # premier appel immédiat
    temps[0] += 2.0
    limiter.attendre()  # doit attendre 6 - 2 = 4 s
    temps[0] += 10.0
    limiter.attendre()  # assez attendu
    assert attentes == [4.0]
