"""Mémoire des habitants : stockage et récupération (SPEC §7.3).

score = poids_recence * decay^heures + poids_importance * importance/10 + poids_pertinence * tfidf
La pertinence est un cosinus TF-IDF en Python pur : pas de dépendance, pas d'appel API.
"""

import math
import re
import unicodedata
from collections import Counter

from rushes.config import MemoireConfig
from rushes.models import Souvenir
from rushes.storage import Storage

MOTS_VIDES = set(
    """le la les un une des du de au aux et ou mais donc car ni que qui quoi dont ce cet cette
    ces mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs je tu il elle on nous
    vous ils elles me te se moi toi lui eux en ne pas plus est sont suis etre avoir ai as ont
    avec pour par sur sous dans chez vers sans tres bien tout tous toute toutes comme si alors
    aussi meme deja encore fait faire""".split()
)


def tokens(texte: str) -> list[str]:
    sans_accents = unicodedata.normalize("NFKD", texte.lower()).encode("ascii", "ignore").decode()
    return [m for m in re.findall(r"[a-z0-9]+", sans_accents) if len(m) > 2 and m not in MOTS_VIDES]


def similarites(requete: str, documents: list[str]) -> list[float]:
    """Cosinus TF-IDF entre la requête et chaque document (0 à 1)."""
    docs = [Counter(tokens(d)) for d in documents]
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log((1 + len(docs)) / (1 + f)) + 1 for t, f in df.items()}
    q = {t: f * idf[t] for t, f in Counter(tokens(requete)).items() if t in idf}
    norme_q = math.sqrt(sum(v * v for v in q.values()))
    resultats = []
    for d in docs:
        v = {t: f * idf[t] for t, f in d.items()}
        norme_v = math.sqrt(sum(x * x for x in v.values()))
        produit = sum(poids * v.get(t, 0.0) for t, poids in q.items())
        resultats.append(produit / (norme_q * norme_v) if norme_q and norme_v else 0.0)
    return resultats


def heures_absolues(jour: int, heure: str) -> float:
    h, m = heure.split(":")
    return (jour - 1) * 24 + int(h) + int(m) / 60


def moment(jour: int, heure: str) -> str:
    return f"j{jour}-{heure}"


def depuis_moment(m: str) -> float:
    jour, heure = m[1:].split("-")
    return heures_absolues(int(jour), heure)


def formater(souvenirs: list[Souvenir]) -> str:
    lignes = [f"- (jour {s.jour}, {s.heure}) {s.contenu}" for s in souvenirs]
    return "\n".join(lignes) or "(aucun souvenir particulier)"


class Memoire:
    def __init__(self, storage: Storage, cfg: MemoireConfig):
        self.storage = storage
        self.cfg = cfg

    def ajouter(
        self,
        habitant_id: str,
        jour: int,
        heure: str,
        type: str,
        contenu: str,
        importance: int,
        mots_cles: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> Souvenir:
        s = Souvenir(
            id=self.storage.prochain_id(Souvenir, "mem"),
            habitant_id=habitant_id,
            jour=jour,
            heure=heure,
            type=type,
            contenu=contenu,
            importance=importance,
            mots_cles=mots_cles or [],
            derniere_consultation=moment(jour, heure),
            sources=sources or [],
        )
        self.storage.put(s)
        return s

    def recuperer(self, habitant_id: str, requete: str, jour: int, heure: str) -> list[Souvenir]:
        """Les `top_k` souvenirs les mieux notés ; leur `derniere_consultation` est mise à jour."""
        souvenirs = self.storage.all(Souvenir, habitant_id=habitant_id)
        if not souvenirs:
            return []
        maintenant = heures_absolues(jour, heure)
        pertinences = similarites(
            requete, [f"{s.contenu} {' '.join(s.mots_cles)}" for s in souvenirs]
        )
        p = self.cfg.poids
        scores = [
            p.recence * self.cfg.decay ** (maintenant - depuis_moment(s.derniere_consultation))
            + p.importance * s.importance / 10
            + p.pertinence * pertinence
            for s, pertinence in zip(souvenirs, pertinences, strict=True)
        ]
        meilleurs = sorted(range(len(souvenirs)), key=lambda i: scores[i], reverse=True)
        elus = []
        for i in meilleurs[: self.cfg.top_k]:
            s = souvenirs[i].model_copy(update={"derniere_consultation": moment(jour, heure)})
            self.storage.put(s)
            elus.append(s)
        return elus
