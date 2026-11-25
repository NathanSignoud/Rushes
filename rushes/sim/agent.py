"""Un habitant qui décide : perception → souvenirs → LLM → validation (SPEC §7.1)."""

from pydantic import ConfigDict

from rushes.config import charger_prompt
from rushes.llm.base import LLMError
from rushes.models import Decision, Habitant, Souvenir
from rushes.sim.actions import valider
from rushes.sim.memory import formater
from rushes.sim.world import Ville, est_ouvert, prenom


def texte_relation(h: Habitant, autre: str) -> str:
    r = h.relations.get(autre)
    if r is None:
        return "tu ne connais pas vraiment cette personne."
    return f"{r.affinite:+d} sur 100. {r.description}"


def texte_secrets(h: Habitant) -> str:
    return " ; ".join(s.contenu for s in h.secrets) or "aucun"


def nommer(ville: Ville, ids: list[str]) -> str:
    return ", ".join(f"{ville.habitants[i].nom} ({i})" for i in ids) or "personne"


def _texte_lieux(ville: Ville, hid: str) -> str:
    lignes = []
    for lieu in ville.lieux.values():
        if lieu.type == "prive":
            etat = "chez toi" if lieu.proprietaire == hid else "privé"
        else:
            etat = "ouvert" if est_ouvert(lieu, ville.heure) else "fermé"
        lignes.append(f"- {lieu.id} : {lieu.nom} ({etat})")
    return "\n".join(lignes)


def _schema_avec_exemples(ville: Ville, hid: str, presents: list[str]) -> type[Decision]:
    """La Décision, avec des exemples valides ici et maintenant dans son JSON Schema.

    Le fournisseur mock y pioche ses réponses ; les vrais fournisseurs ne voient que le prompt.
    """
    ici = ville.positions[hid]
    exemples: list[dict] = [
        {"pensee": "Voyons voir.", "action": "observer", "arguments": {}, "importance": 2},
        {
            "pensee": "Au travail.",
            "action": "faire",
            "arguments": {"activite": "s'occuper"},
            "duree_ticks": 2,
            "importance": 2,
        },
    ]
    exemples += [
        {
            "pensee": f"Tiens, {prenom(ville.habitants[p])}.",
            "action": "parler_a",
            "arguments": {"habitant": p, "intention": "discuter"},
            "importance": 3,
        }
        for p in presents
    ]
    ailleurs = [
        lieu.id
        for lieu in ville.lieux.values()
        if lieu.id != ici and lieu.type == "public" and est_ouvert(lieu, ville.heure)
    ]
    if ailleurs:
        exemples.append(
            {
                "pensee": "Je bouge.",
                "action": "aller_a",
                "arguments": {"lieu": ailleurs[0]},
                "importance": 2,
            }
        )
    config = ConfigDict(json_schema_extra={"examples": exemples})
    return type("Decision", (Decision,), {"model_config": config})


def decider(ville: Ville, hid: str) -> tuple[Decision, list[Souvenir]]:
    h = ville.habitants[hid]
    lieu = ville.lieux[ville.positions[hid]]
    presents = ville.presents(lieu.id, sauf=hid)
    recents = [e.contenu for e in ville.evenements_recents(lieu.id)]
    plan = f"Pas de plan précis. Ta routine : {h.routine}"  # plan du jour : phase 2
    requete = " ".join([lieu.nom, *(ville.habitants[p].nom for p in presents), *recents, plan])
    souvenirs = ville.memoire.recuperer(hid, requete, ville.jour, ville.heure)
    prompt = charger_prompt("habitant_decision").format(
        nom=h.nom,
        age=h.age,
        metier=h.metier,
        nom_ville=ville.nom,
        description=h.description,
        traits=", ".join(h.traits),
        facon_de_parler=h.facon_de_parler,
        objectifs=" ; ".join(h.objectifs),
        secrets=texte_secrets(h),
        relations="\n".join(
            f"- {ville.habitants[i].nom} ({i}) : {texte_relation(h, i)}" for i in h.relations
        ),
        plan_du_jour=plan,
        souvenirs=formater(souvenirs),
        jour=ville.jour,
        heure=ville.heure,
        lieu=lieu.nom,
        description_lieu=lieu.description,
        presents=nommer(ville, presents),
        evenements_recents="\n".join(f"- {r}" for r in recents) or "(rien de notable)",
        liste_lieux=_texte_lieux(ville, hid),
    )
    schema = _schema_avec_exemples(ville, hid, presents)
    t = ville.config.llm.temperature.habitant
    try:
        d = ville.llm.complete_json(prompt, schema, temperature=t, tag="decision")
        erreur = valider(ville, hid, d)
        if erreur:  # renvoyée une fois au modèle, puis repli sur « observer »
            refus = charger_prompt("action_refusee").format(action=d.action, erreur=erreur)
            d = ville.llm.complete_json(
                f"{prompt}\n\n{refus}", schema, temperature=t, tag="decision"
            )
            if valider(ville, hid, d):
                d = Decision(pensee=d.pensee, action="observer", importance=d.importance)
    except LLMError:
        d = Decision(pensee="", action="observer", importance=1)
    return d, souvenirs
