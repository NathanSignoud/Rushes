import json
from contextlib import closing

import pytest

from rushes.__main__ import main
from rushes.config import charger_config
from rushes.llm.base import LLMProvider
from rushes.llm.budget import Budget, BudgetEpuise
from rushes.llm.mock import MockProvider
from rushes.models import (
    Conversation,
    Decision,
    Evenement,
    Habitant,
    Lieu,
    ReponseDialogue,
    ResumeConversation,
    Souvenir,
)
from rushes.sim.actions import valider
from rushes.sim.engine import simuler
from rushes.sim.memory import Memoire
from rushes.sim.world import Ville
from rushes.storage import Storage

LIRE = {"pensee": "…", "action": "faire", "arguments": {"activite": "lire"}, "duree_ticks": 8}


class Scenario(LLMProvider):
    """Jour 1, 07:00 : Léa aborde Inès (2 répliques). Le reste du temps, tout le monde lit."""

    def __init__(self, decisions_lea_j1: list[dict] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.prompts: list[str] = []
        self.decisions_lea_j1 = decisions_lea_j1

    def _generate(self, messages, schema, temperature):
        prompt = messages[-1]["content"]
        self.prompts.append(prompt)
        lea_j1 = prompt.startswith("Tu es Léa") and "jour 1, il est 07:00" in prompt
        if issubclass(schema, Decision) and lea_j1 and self.decisions_lea_j1 is not None:
            reponse = self.decisions_lea_j1.pop(0)
        elif issubclass(schema, Decision) and lea_j1:
            reponse = {
                "pensee": "Je tente ma chance.",
                "action": "parler_a",
                "arguments": {"habitant": "ines", "intention": "parler du ciné-club"},
                "importance": 4,
            }
        elif issubclass(schema, Decision):
            reponse = {**LIRE, "importance": 1}
        elif schema is ReponseDialogue:
            premier = "(personne n'a encore parlé)" in prompt
            reponse = {"pensee": "", "replique": "Un ciné-club ?", "fin": not premier}
        elif schema is ResumeConversation:
            reponse = {
                "souvenir": "On a parlé du ciné-club au Zinc.",
                "importance": 6,
                "delta_affinite": 3,
                "secrets_appris": [],
            }
        return json.dumps(reponse), 10


@pytest.fixture
def base(projet):
    assert main(["init"]) == 0
    config = charger_config()
    config.sim.fin_journee = "09:00"  # 4 ticks par jour
    with closing(Storage(projet / "data" / "rushes.sqlite")) as s:
        yield s, config


def test_lea_et_ines_se_souviennent_le_lendemain(base):
    s, config = base
    llm = Scenario()
    simuler(s, llm, config, jours=2, habitants=["lea", "ines"], depart="cafe")

    (conv,) = s.all(Conversation)
    assert conv.participants == ["lea", "ines"] and len(conv.tours) == 2
    dialogues = [e for e in s.all(Evenement) if e.type == "dialogue"]
    assert [e.contenu for e in dialogues] == [
        "Léa : « Un ciné-club ? »",
        "Inès : « Un ciné-club ? »",
    ]
    souvenir_lea = next(m for m in s.all(Souvenir, habitant_id="lea") if m.type == "conversation")

    # Jour 2 : la première décision de Léa remonte la conversation en tête de ses souvenirs…
    decision_j2 = next(e for e in s.all(Evenement) if e.jour == 2 and e.acteurs == ["lea"])
    assert decision_j2.details["souvenirs"][0] == souvenir_lea.id
    # … et ce souvenir figure dans son prompt.
    prompt_j2 = next(p for p in llm.prompts if p.startswith("Tu es Léa") and "jour 2" in p)
    assert "On a parlé du ciné-club au Zinc." in prompt_j2
    assert s.get_meta("prochain_jour") == "3"


def test_action_invalide_corrigee_puis_repli_sur_observer(base):
    s, config = base
    lune = {"pensee": "", "action": "aller_a", "arguments": {"lieu": "lune"}, "importance": 2}
    llm = Scenario(decisions_lea_j1=[lune, lune])
    simuler(s, llm, config, jours=1, habitants=["lea", "ines"], depart="cafe")
    refus = [p for p in llm.prompts if "lieu inconnu 'lune'" in p]
    assert len(refus) == 1  # l'erreur est renvoyée une seule fois
    premiere = next(e for e in s.all(Evenement) if e.acteurs == ["lea"])
    assert premiere.contenu == "Léa observe les alentours."


def test_validation_des_actions(base):
    s, config = base
    ville = Ville(
        storage=s,
        llm=Scenario(),
        config=config,
        memoire=Memoire(s, config.memoire),
        nom="Vaudrecourt",
        lieux={lieu.id: lieu for lieu in s.all(Lieu)},
        habitants={h.id: h for h in s.all(Habitant)},
        actifs=["lea", "ines"],
        tick=40,
        heure="13:30",
        positions={"lea": "cafe", "ines": "cafe"},
        derniere_conversation={frozenset(("lea", "ines")): 38},
    )

    def d(action, **args):
        return Decision(pensee="", action=action, arguments=args, importance=1)

    assert "privé" in valider(ville, "lea", d("aller_a", lieu="maison_gerard"))
    assert valider(ville, "lea", d("aller_a", lieu="maison_lea")) is None
    assert "fermé" in valider(ville, "lea", d("aller_a", lieu="boulangerie"))  # 13:30
    assert "déjà" in valider(ville, "lea", d("aller_a", lieu="cafe"))
    assert "n'est pas ici" in valider(ville, "lea", d("parler_a", habitant="gerard"))
    assert "venez de vous parler" in valider(ville, "lea", d("parler_a", habitant="ines"))
    ville.tick = 42  # la pause anti-boucle est passée
    assert valider(ville, "lea", d("parler_a", habitant="ines")) is None
    assert "activité" in valider(ville, "lea", d("faire", activite=" "))


def test_budget_atteint_arret_propre(base):
    s, config = base
    llm = MockProvider(seed=1, budget=Budget(max_appels=3))
    with pytest.raises(BudgetEpuise):
        simuler(s, llm, config, jours=2, habitants=["lea", "ines"], depart="cafe")
    assert llm.budget.appels == 3
    assert s.all(Evenement)[-1].type == "systeme"
    assert s.get_meta("prochain_jour") == "2"  # la journée écourtée compte comme simulée


def test_habitant_inconnu(base):
    s, config = base
    with pytest.raises(ValueError, match="fantome"):
        simuler(s, Scenario(), config, jours=1, habitants=["fantome"])
