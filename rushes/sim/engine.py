"""Boucle principale de la simulation (SPEC §7.1)."""

import random

from rushes.config import Config
from rushes.llm.base import LLMProvider
from rushes.llm.budget import BudgetEpuise
from rushes.models import Habitant, Lieu
from rushes.sim.actions import executer
from rushes.sim.agent import decider
from rushes.sim.conversation import converser
from rushes.sim.memory import Memoire
from rushes.sim.world import Horloge, Ville
from rushes.storage import Storage


def simuler(
    storage: Storage,
    llm: LLMProvider,
    config: Config,
    jours: int,
    habitants: list[str] | None = None,
    depart: str | None = None,
) -> None:
    """Simule `jours` journées à partir du prochain jour non simulé.

    `habitants` restreint la simulation à certains habitants ; `depart` les fait tous commencer
    la journée au même lieu au lieu de chez eux. Lève BudgetEpuise si le budget est atteint
    (la journée en cours est alors écourtée et comptée comme simulée).
    """
    tous = {h.id: h for h in storage.all(Habitant)}
    lieux = {lieu.id: lieu for lieu in storage.all(Lieu)}
    actifs = habitants or sorted(tous)
    inconnus = [h for h in actifs if h not in tous] + (
        [depart] if depart and depart not in lieux else []
    )
    if inconnus:
        raise ValueError(f"Inconnus dans la base : {', '.join(inconnus)}")
    ville = Ville(
        storage=storage,
        llm=llm,
        config=config,
        memoire=Memoire(storage, config.memoire),
        nom=storage.get_meta("nom_ville") or "",
        lieux=lieux,
        habitants=tous,
        actifs=actifs,
    )
    horloge = Horloge(config.sim)
    seed = storage.get_meta("seed")
    for _ in range(jours):
        ville.jour = int(storage.get_meta("prochain_jour") or 1)
        ville.positions = {h: depart or tous[h].domicile for h in actifs}
        ville.occupe_jusqua, ville.endormis, ville.derniere_conversation = {}, set(), {}
        rng = random.Random(f"{seed}-{ville.jour}")
        try:
            for i in range(horloge.ticks_par_jour):
                ville.tick, ville.heure = horloge.tick(ville.jour, i), horloge.heure(i)
                ville.ont_agi = set()
                ordre = sorted(actifs)
                rng.shuffle(ordre)
                for hid in ordre:
                    if hid in ville.endormis or hid in ville.ont_agi:
                        continue
                    if ville.occupe_jusqua.get(hid, -1) > ville.tick:
                        continue  # action longue en cours : pas d'appel LLM
                    d, souvenirs = decider(ville, hid)
                    if d.action == "parler_a":
                        converser(ville, hid, d, souvenirs)
                    else:
                        executer(ville, hid, d, souvenirs)
                    ville.ont_agi.add(hid)
        except BudgetEpuise as e:
            ville.evenement("systeme", f"Journée interrompue à {ville.heure} : {e}")
            raise
        finally:
            storage.set_meta("prochain_jour", str(ville.jour + 1))
