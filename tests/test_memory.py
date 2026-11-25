from contextlib import closing

import pytest

from rushes.config import RACINE, charger_config
from rushes.sim.memory import Memoire, similarites, tokens
from rushes.storage import Storage


@pytest.fixture
def memoire(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        yield Memoire(s, charger_config(RACINE / "config.yaml").memoire)


def test_tokens_sans_accents_ni_mots_vides():
    assert tokens("Inès a vu l'école, et le CINÉ-club !") == ["ines", "ecole", "cine", "club"]


def test_similarite_classe_le_document_pertinent():
    docs = ["Gérard a brûlé ses baguettes.", "Inès m'a parlé du ciné-club.", "Il pleut."]
    scores = similarites("ciné-club avec Inès", docs)
    assert scores.index(max(scores)) == 1
    assert scores[2] == 0.0


def test_recuperer_pertinence_et_top_k(memoire):
    memoire.cfg.top_k = 2
    for contenu in ("Le pain était bon.", "Inès m'a parlé du ciné-club.", "Il pleut sur la place."):
        memoire.ajouter("lea", 1, "08:00", "observation", contenu, 3)
    elus = memoire.recuperer("lea", "Inès Haddad", 1, "09:00")
    assert len(elus) == 2
    assert elus[0].contenu == "Inès m'a parlé du ciné-club."
    assert elus[0].derniere_consultation == "j1-09:00"  # consultation enregistrée
    assert memoire.recuperer("ines", "Inès", 1, "09:00") == []  # mémoires séparées


def test_recence_et_importance(memoire):
    memoire.ajouter("lea", 1, "08:00", "observation", "Une matinée calme.", 3)
    memoire.ajouter("lea", 5, "08:00", "observation", "Une matinée calme.", 3)
    memoire.ajouter("lea", 1, "08:00", "observation", "Une matinée calme.", 9)
    elus = memoire.recuperer("lea", "rien à voir", 5, "09:00")
    assert [(s.jour, s.importance) for s in elus] == [(1, 9), (5, 3), (1, 3)]
