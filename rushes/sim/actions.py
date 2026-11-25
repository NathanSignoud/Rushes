"""Outils des habitants : validation et exécution des décisions (SPEC §7.2).

`parler_a` est exécuté par `conversation.converser`.
"""

from rushes.models import Decision, Souvenir
from rushes.sim.world import Ville, est_ouvert, prenom

PAUSE_CONVERSATION = 4  # ticks avant qu'une même paire puisse se reparler (anti-boucle, §18)


def valider(ville: Ville, hid: str, d: Decision) -> str | None:
    """Renvoie la raison du refus, ou None si l'action est possible."""
    ici = ville.positions[hid]
    args = d.arguments
    match d.action:
        case "aller_a":
            lieu = ville.lieux.get(str(args.get("lieu", "")))
            if lieu is None:
                return f"lieu inconnu {args.get('lieu')!r} : utilise un id de la liste des lieux."
            if lieu.id == ici:
                return f"tu es déjà à cet endroit ({lieu.nom})."
            if lieu.type == "prive" and lieu.proprietaire != hid:
                return f"{lieu.nom} est privé : on n'y entre pas sans invitation."
            if not est_ouvert(lieu, ville.heure):
                return f"{lieu.nom} est fermé à cette heure (horaires : {lieu.horaires})."
        case "parler_a":
            cible = str(args.get("habitant", ""))
            if cible not in ville.presents(ici, sauf=hid):
                return f"{cible!r} n'est pas ici."
            derniere = ville.derniere_conversation.get(frozenset((hid, cible)))
            if derniere is not None and ville.tick - derniere < PAUSE_CONVERSATION:
                return "vous venez de vous parler : laisse passer un peu de temps."
        case "faire":
            if not str(args.get("activite", "")).strip():
                return "précise l'activité dans arguments.activite."
    return None


def executer(ville: Ville, hid: str, d: Decision, souvenirs: list[Souvenir]) -> None:
    """Applique une décision déjà validée (sauf parler_a), logue l'événement et le souvenir."""
    h = ville.habitants[hid]
    lieu = ville.lieux[ville.positions[hid]]
    match d.action:
        case "aller_a":
            lieu = ville.lieux[str(d.arguments["lieu"])]
            ville.positions[hid] = lieu.id
            public, vecu = f"{prenom(h)} va vers {lieu.nom}.", f"Je vais vers {lieu.nom}."
        case "faire":
            activite = str(d.arguments["activite"])
            ville.occupe_jusqua[hid] = ville.tick + d.duree_ticks
            public, vecu = f"{prenom(h)} s'occupe : {activite}.", f"Je m'occupe : {activite}."
        case "rentrer_dormir":
            lieu = ville.lieux[h.domicile]
            ville.positions[hid] = lieu.id
            ville.endormis.add(hid)
            public, vecu = f"{prenom(h)} rentre se coucher.", "Je rentre me coucher."
        case _:  # observer
            presents = [prenom(ville.habitants[p]) for p in ville.presents(lieu.id, sauf=hid)]
            vus = [e.contenu for e in ville.evenements_recents(lieu.id)][-3:]
            public = f"{prenom(h)} observe les alentours."
            vecu = f"J'observe ce qui se passe ici ({lieu.nom}). Présents : " + (
                ", ".join(presents) or "personne"
            )
            vecu += "." + "".join(f" {v}" for v in vus)
    temoins = ville.presents(lieu.id, sauf=hid)
    evt = ville.evenement(
        "deplacement" if d.action in ("aller_a", "rentrer_dormir") else "action",
        public,
        lieu=lieu.id,
        acteurs=[hid],
        temoins=temoins,
        pensee=d.pensee or None,
        importance=d.importance,
        details={"souvenirs": [s.id for s in souvenirs]},
    )
    ville.memoire.ajouter(
        hid,
        ville.jour,
        ville.heure,
        "observation",
        f"{vecu} {d.pensee}".strip(),
        d.importance,
        mots_cles=[lieu.id, *temoins],
        sources=[evt.id],
    )
