"""Conversations au tour par tour (SPEC §7.5) : une réplique = un appel, chacun avec sa mémoire."""

from rushes.config import charger_prompt
from rushes.llm.base import LLMError
from rushes.models import Conversation, Decision, ReponseDialogue, ResumeConversation, Souvenir
from rushes.sim.agent import nommer, texte_relation, texte_secrets
from rushes.sim.memory import formater
from rushes.sim.world import Ville, prenom


def converser(ville: Ville, a_id: str, d: Decision, souvenirs: list[Souvenir]) -> Conversation:
    """`a_id` a décidé `parler_a` (décision déjà validée) : dialogue, puis résumé par chacun."""
    b_id = str(d.arguments["habitant"])
    intention = str(d.arguments.get("intention", "discuter"))
    a, b = ville.habitants[a_id], ville.habitants[b_id]
    lieu = ville.lieux[ville.positions[a_id]]
    temoins = [p for p in ville.presents(lieu.id) if p not in (a_id, b_id)]
    t = ville.config.llm.temperature.habitant
    ville.evenement(
        "action",
        f"{prenom(a)} aborde {prenom(b)}.",
        lieu=lieu.id,
        acteurs=[a_id, b_id],
        temoins=temoins,
        pensee=d.pensee or None,
        importance=d.importance,
        details={"souvenirs": [s.id for s in souvenirs], "intention": intention},
    )
    conv = Conversation(
        id=ville.storage.prochain_id(Conversation, "conv"),
        participants=[a_id, b_id],
        lieu=lieu.id,
        debut=f"j{ville.jour}-{ville.heure}",
    )
    historique: list[str] = []
    for tour in range(ville.config.dialogue.max_tours):
        loc, autre = (a, b) if tour % 2 == 0 else (b, a)
        dernier = historique[-1] if historique else ""
        lui = ville.memoire.recuperer(
            loc.id, f"{autre.nom} {intention} {dernier}", ville.jour, ville.heure
        )
        prompt = charger_prompt("habitant_dialogue").format(
            nom=loc.nom,
            description=loc.description,
            traits=", ".join(loc.traits),
            facon_de_parler=loc.facon_de_parler,
            secrets=texte_secrets(loc),
            interlocuteur=autre.nom,
            lieu=lieu.nom,
            relation=texte_relation(loc, autre.id),
            souvenirs=formater(lui),
            intention=intention if loc is a else f"{prenom(a)} vient te parler. À toi de voir.",
            temoins=nommer(ville, temoins),
            historique="\n".join(historique) or "(personne n'a encore parlé)",
        )
        try:
            r = ville.llm.complete_json(prompt, ReponseDialogue, temperature=t, tag="dialogue")
        except LLMError:
            break
        ligne = f"{prenom(loc)} : « {r.replique} »"
        evt = ville.evenement(
            "dialogue",
            ligne,
            lieu=lieu.id,
            acteurs=[loc.id, autre.id],
            temoins=temoins,
            pensee=r.pensee or None,
            importance=d.importance,
            details={
                "conversation_id": conv.id,
                "tour": tour + 1,
                "souvenirs": [s.id for s in lui],
            },
        )
        conv.tours.append(evt.id)
        historique.append(ligne)
        if r.fin:
            break
    conv.fin = f"j{ville.jour}-{ville.heure}"
    for loc, autre in ((a, b), (b, a)) if historique else ():
        prompt = charger_prompt("habitant_resume_conversation").format(
            nom=loc.nom,
            traits=", ".join(loc.traits),
            interlocuteur=autre.nom,
            lieu=lieu.nom,
            relation=texte_relation(loc, autre.id),
            conversation="\n".join(historique),
        )
        try:
            r = ville.llm.complete_json(
                prompt, ResumeConversation, temperature=t, tag="resume_conversation"
            )
        except LLMError:
            continue
        ville.memoire.ajouter(
            loc.id,
            ville.jour,
            ville.heure,
            "conversation",
            r.souvenir,
            r.importance,
            mots_cles=[autre.id, lieu.id],
            sources=conv.tours,
        )
        conv.resume_par_participant[loc.id] = r.souvenir
        conv.deltas_affinite[loc.id] = r.delta_affinite  # appliqués en phase 3
        conv.secrets_reveles += r.secrets_appris  # rapprochés des ids de secrets en phase 3
    ville.storage.put(conv)
    ville.derniere_conversation[frozenset((a_id, b_id))] = ville.tick
    ville.ont_agi |= {a_id, b_id}
    return conv
