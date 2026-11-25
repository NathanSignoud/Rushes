"""Horloge, lieux et état courant de la ville pendant une simulation."""

from dataclasses import dataclass, field
from typing import Any

from rushes.config import Config, SimConfig
from rushes.llm.base import LLMProvider
from rushes.models import Evenement, Habitant, Lieu
from rushes.sim.memory import Memoire
from rushes.storage import Storage


def minutes(heure: str) -> int:
    h, m = heure.split(":")
    return int(h) * 60 + int(m)


def est_ouvert(lieu: Lieu, heure: str) -> bool:
    if not lieu.horaires:
        return True
    plages = (plage.split("-") for plage in lieu.horaires.split(","))
    return any(minutes(debut) <= minutes(heure) < minutes(fin) for debut, fin in plages)


def prenom(h: Habitant) -> str:
    return h.nom.split()[0]


class Horloge:
    """1 tick = `minutes_par_tick`. Le tick est global : il continue d'un jour à l'autre."""

    def __init__(self, sim: SimConfig):
        self.debut = minutes(sim.debut_journee)
        self.pas = sim.minutes_par_tick
        self.ticks_par_jour = (minutes(sim.fin_journee) - self.debut) // self.pas

    def heure(self, i: int) -> str:
        m = self.debut + i * self.pas
        return f"{m // 60:02d}:{m % 60:02d}"

    def tick(self, jour: int, i: int) -> int:
        return (jour - 1) * self.ticks_par_jour + i


@dataclass
class Ville:
    storage: Storage
    llm: LLMProvider
    config: Config
    memoire: Memoire
    nom: str
    lieux: dict[str, Lieu]
    habitants: dict[str, Habitant]  # tous, pour les noms ; seuls `actifs` sont simulés
    actifs: list[str]
    jour: int = 1
    tick: int = 0
    heure: str = "07:00"
    positions: dict[str, str] = field(default_factory=dict)
    occupe_jusqua: dict[str, int] = field(default_factory=dict)
    endormis: set[str] = field(default_factory=set)
    ont_agi: set[str] = field(default_factory=set)
    derniere_conversation: dict[frozenset[str], int] = field(default_factory=dict)

    def presents(self, lieu: str, sauf: str | None = None) -> list[str]:
        return [
            h
            for h, ici in self.positions.items()
            if ici == lieu and h != sauf and h not in self.endormis
        ]

    def evenements_recents(self, lieu: str) -> list[Evenement]:
        """Ce qui s'est passé de visible ici depuis le tick précédent."""
        evts = self.storage.evenements(depuis_tick=self.tick - 1, lieu=lieu)
        return [e for e in evts if e.visibilite == "public"][-8:]

    def evenement(self, type: str, contenu: str, **champs: Any) -> Evenement:
        evt = Evenement(
            id=self.storage.prochain_id(Evenement, "evt"),
            jour=self.jour,
            heure=self.heure,
            tick=self.tick,
            type=type,
            contenu=contenu,
            **champs,
        )
        self.storage.add_event(evt)
        return evt
