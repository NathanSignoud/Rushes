"""Tous les schémas pydantic du projet (SPEC §6). Les sorties de LLM sont validées contre eux."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# Les `examples` servent aussi au fournisseur mock pour produire des valeurs valides.
Heure = Annotated[
    str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", examples=["08:00", "12:30", "18:30"])
]
Moment = Annotated[
    str, Field(pattern=r"^j\d+-([01]\d|2[0-3]):[0-5]\d$", examples=["j1-08:00", "j2-18:30"])
]
Horaires = Annotated[
    str,
    Field(
        pattern=r"^\d\d:\d\d-\d\d:\d\d(,\d\d:\d\d-\d\d:\d\d)*$",
        examples=["07:00-22:00", "06:30-13:00,16:00-19:00"],
    ),
]
Importance = Annotated[int, Field(ge=1, le=10)]
Note10 = Annotated[int, Field(ge=0, le=10)]
Affinite = Annotated[int, Field(ge=-100, le=100)]
Pourcent = Annotated[int, Field(ge=0, le=100)]


# --- Ville (§6.2, §15) ---


class Lieu(BaseModel):
    id: str
    nom: str
    description: str
    type: Literal["public", "prive"]
    proprietaire: str | None = None
    horaires: Horaires | None = None  # plages séparées par des virgules ; fermé hors horaires
    voisins: list[str] = []


class Monde(BaseModel):
    nom: str
    description: str
    lieux: list[Lieu]


# --- Habitant (§6.3) ---


class BigFive(BaseModel):
    ouverture: Pourcent
    conscienciosite: Pourcent
    extraversion: Pourcent
    agreabilite: Pourcent
    nevrosisme: Pourcent


class Secret(BaseModel):
    id: str
    contenu: str
    connu_de: list[str] = []


class Relation(BaseModel):
    affinite: Affinite
    description: str


class Habitant(BaseModel):
    id: str
    nom: str
    age: int = Field(ge=0)
    metier: str
    domicile: str
    lieu_travail: str | None = None
    description: str
    traits: list[str]
    big_five: BigFive
    facon_de_parler: str
    objectifs: list[str]
    secrets: list[Secret] = []
    routine: str
    relations: dict[str, Relation] = {}


# --- Mémoire et événements (§6.4, §6.5, §6.6) ---


class Souvenir(BaseModel):
    id: str
    habitant_id: str
    jour: int = Field(ge=1)
    heure: Heure
    type: Literal["observation", "conversation", "reflexion", "plan"]
    contenu: str
    importance: Importance
    mots_cles: list[str] = []
    derniere_consultation: Moment
    sources: list[str] = []


class Evenement(BaseModel):
    id: str
    jour: int = Field(ge=1)
    heure: Heure
    tick: int = Field(ge=0)
    type: Literal[
        "deplacement",
        "action",
        "dialogue",
        "pensee",
        "reflexion",
        "plan",
        "revelation",
        "relation",
        "intervention",
        "systeme",
    ]
    lieu: str | None = None
    acteurs: list[str] = []
    temoins: list[str] = []
    contenu: str
    pensee: str | None = None
    details: dict[str, Any] = {}
    visibilite: Literal["public", "prive"] = "public"
    importance: Importance = 1
    tags: list[str] = []
    intensite: Note10 | None = None
    source: Literal["simulation", "producteur"] = "simulation"


class Conversation(BaseModel):
    id: str
    participants: list[str]
    lieu: str
    debut: Moment
    fin: Moment | None = None
    tours: list[str] = []  # event_ids
    resume_par_participant: dict[str, str] = {}
    secrets_reveles: list[str] = []
    deltas_affinite: dict[str, int] = {}


# --- Salle d'écriture (§6.7, §6.8, §6.9) ---


class Arc(BaseModel):
    id: str
    titre: str
    type: Literal["conflit", "romance", "secret", "ambition", "mystere", "comique"]
    personnages: list[str]
    statut: Literal["mise_en_place", "montee", "climax", "resolu", "abandonne"]
    resume: str
    evenements_cles: list[str] = []
    tension: Note10
    questions_ouvertes: list[str] = []
    derniere_maj: str


class Replique(BaseModel):
    perso: str
    texte: str
    sources: list[str]


class Scene(BaseModel):
    id: str
    lieu: str
    moment: Moment
    personnages: list[str]
    intention: str
    didascalies: str
    repliques: list[Replique]
    fidelite: Literal["fidele", "embelli", "invente"] | None = None


class StatsEpisode(BaseModel):
    appels_llm: int = 0
    tokens: int = 0


class Episode(BaseModel):
    numero: int = Field(ge=1)
    titre: str
    jours_couverts: list[int]
    precedemment: str | None = None
    cold_open: Scene | None = None
    scenes: list[Scene]
    cliffhanger: str
    arcs: list[str] = []
    interventions_utilisees: list[str] = []
    stats: StatsEpisode = StatsEpisode()


class Intervention(BaseModel):
    id: str
    jour: int = Field(ge=1)
    heure: Heure
    type: Literal[
        "evenement_public", "lettre_anonyme", "rumeur", "nouvel_arrivant", "rendez_vous_fortuit"
    ]
    cibles: list[str] = []
    contenu: str
    objectif_narratif: str
    arc_vise: str | None = None
    resultat: str | None = None
