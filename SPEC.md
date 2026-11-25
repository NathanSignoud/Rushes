# RUSHES — Spécification du projet

> *Une petite ville peuplée d'agents IA vit sa vie. Un showrunner IA la regarde, repère les histoires, provoque des rebondissements… et en fait une série.*

Nom de code : **Rushes** (renommable). Langue du contenu généré : **français**.

---

## 0. Comment utiliser ce document (pour Claude Code)

- Ce fichier est la **source de vérité** du projet. Lis-le en entier avant de coder.
- On avance **phase par phase** (voir §13). À la fin de chaque phase : tests verts, commit, puis **tu t'arrêtes et tu résumes** ce qui a été fait, ce qui reste et les décisions prises. Tu attends ma validation avant la phase suivante.
- Si une décision n'est pas couverte ici, choisis l'option la plus simple, note-la dans `docs/DECISIONS.md` et signale-la dans ton résumé.
- Les noms de modèles et les limites des offres gratuites changent souvent : **vérifie la documentation actuelle** des fournisseurs avant de les écrire dans la config.

---

## 1. Vision

Deux couches :

1. **La ville** : une simulation multi-agents à la « Generative Agents » (Stanford, 2023). Cinq habitants ont chacun une personnalité, une mémoire, des secrets et des objectifs contradictoires. Ils vivent, se déplacent, discutent, se souviennent et réfléchissent.
2. **Le showrunner** : une salle d'écriture multi-agents qui lit les logs de la ville (les « rushes »), repère les arcs dramatiques et produit des **épisodes** (script, puis audio, puis vidéo). Il peut aussi **intervenir dans la ville** comme un producteur de télé-réalité (lettre anonyme, fête, nouvel arrivant…) sans jamais contrôler les habitants directement.

Résultat attendu : une page web « Saison 1 » avec des épisodes générés à partir de ce qui s'est *réellement* passé dans la simulation.

---

## 2. Objectifs et contraintes

### Objectifs pédagogiques (prioritaires)
- Comprendre la **boucle agentique** en la codant **à la main** : perception → récupération mémoire → décision → action → observation.
- Tool calling, sorties structurées, mémoire longue (RAG), réflexion, planification.
- Pipelines **multi-agents** avec des rôles distincts.
- Un agent (le producteur) qui **planifie et agit** sur un environnement qu'il ne contrôle pas.
- Mesurer : coût, nombre d'appels, cohérence.

### Contraintes techniques
- **Aucun framework d'agents** (pas de LangChain, LangGraph, CrewAI, AutoGen…). Python pur et quelques bibliothèques utilitaires.
- **LLM via API gratuite** (offre gratuite Gemini ou Groq), derrière une couche d'abstraction. Un **fournisseur factice (mock)** permet de tout tester sans réseau ni quota.
- Respect des **limites de débit** : rate limiter, retries, budget d'appels par exécution.
- Clés API dans `.env` uniquement, jamais commitées.

---

## 3. Stack

| Besoin | Choix |
|---|---|
| Langage | Python 3.11+ |
| Validation / schémas | pydantic v2 |
| Client LLM | `openai` (SDK) pointé vers les endpoints compatibles OpenAI de Gemini / Groq (à vérifier dans leur doc) |
| Config | YAML (`config.yaml`) + `.env` (python-dotenv) |
| Stockage | SQLite (stdlib `sqlite3`) + export JSONL des événements |
| Web | FastAPI + uvicorn + Jinja2, JS vanilla (pas de build front) |
| Tests | pytest |
| Qualité | ruff (lint + format) |
| Audio (phase 7) | TTS local léger (ex. Piper, voix FR) — à valider le moment venu |
| Montage (phase 8) | ffmpeg |

---

## 4. Architecture

```
                   ┌────────────────────────────────────────────┐
                   │                  LA VILLE                  │
                   │                                            │
  config.yaml ───▶ │  World (horloge, lieux)                    │
  casting/*.json ─▶│  Agents (fiche, mémoire, plan, relations)  │
                   │  SimulationEngine (boucle de ticks)        │
                   └───────────────┬────────────────────────────┘
                                   │ écrit chaque événement
                                   ▼
                     EventLog (SQLite + events.jsonl)  ◀── interventions
                                   │                         ▲
                                   ▼                         │
                   ┌────────────────────────────────────────┴───┐
                   │              LA SALLE D'ÉCRITURE           │
                   │                                            │
                   │  1. Dérusheur   → tags + intensité         │
                   │  2. Showrunner  → arcs, choix intrigues    │
                   │  3. Scénariste  → scènes + dialogues       │
                   │  4. Monteur     → cold open, cliffhanger   │
                   │  5. Fact-checker→ fidélité aux logs        │
                   │  6. Producteur  → interventions dans la ville
                   └───────────────┬────────────────────────────┘
                                   ▼
                   Épisodes (JSON + Markdown) → Web / Audio / Vidéo
```

Toute communication avec un LLM passe par `rushes/llm/` (aucun appel direct ailleurs).

---

## 5. Arborescence du dépôt

```
rushes/
├── CLAUDE.md
├── SPEC.md                    # ce fichier
├── README.md
├── config.yaml
├── .env.example               # GEMINI_API_KEY=, GROQ_API_KEY=
├── .gitignore                 # .env, data/, __pycache__, *.sqlite
├── pyproject.toml
├── casting/
│   ├── world.json             # ville + lieux
│   └── habitants/*.json       # une fiche par habitant
├── prompts/                   # templates en .md avec {placeholders}
│   ├── habitant_plan_jour.md
│   ├── habitant_decision.md
│   ├── habitant_dialogue.md
│   ├── habitant_resume_conversation.md
│   ├── habitant_reflexion.md
│   ├── derusheur.md
│   ├── showrunner_arcs.md
│   ├── scenariste.md
│   ├── monteur.md
│   ├── fact_checker.md
│   └── producteur.md
├── rushes/
│   ├── __init__.py
│   ├── __main__.py            # CLI
│   ├── config.py
│   ├── models.py              # tous les schémas pydantic
│   ├── storage.py             # SQLite + JSONL
│   ├── llm/
│   │   ├── base.py            # interface LLMProvider
│   │   ├── openai_compat.py   # Gemini / Groq
│   │   ├── mock.py            # réponses déterministes
│   │   ├── ratelimit.py
│   │   └── budget.py          # compteur appels/tokens, plafond
│   ├── sim/
│   │   ├── world.py
│   │   ├── agent.py
│   │   ├── memory.py          # stockage + récupération
│   │   ├── actions.py         # outils des habitants
│   │   ├── conversation.py
│   │   ├── reflection.py
│   │   └── engine.py          # boucle principale
│   ├── show/
│   │   ├── derusheur.py
│   │   ├── arcs.py
│   │   ├── scenariste.py
│   │   ├── monteur.py
│   │   ├── fact_checker.py
│   │   ├── producteur.py
│   │   └── export.py          # épisode → Markdown
│   ├── media/                 # phases 7-8
│   │   ├── tts.py
│   │   └── video.py
│   └── web/
│       ├── app.py
│       ├── templates/
│       └── static/
├── tests/
├── data/                      # généré, ignoré par git
│   ├── rushes.sqlite
│   ├── events.jsonl
│   └── episodes/
└── docs/
    └── DECISIONS.md
```

---

## 6. Modèle de données

Tous les schémas sont définis en pydantic dans `rushes/models.py`. Les sorties des LLM sont **toujours** validées contre ces schémas (§9).

### 6.1 Temps
- 1 **tick** = 30 minutes simulées.
- Journée active : 07:00 → 23:00 (32 ticks). La nuit est sautée en un seul pas (les habitants dorment).
- Le temps simulé est stocké sous la forme `jour` (int, à partir de 1) + `heure` ("HH:MM").

### 6.2 Lieu
```json
{
  "id": "cafe",
  "nom": "Le Zinc",
  "description": "Le café-tabac de la place, cœur des ragots du village.",
  "type": "public",            // public | prive
  "proprietaire": "ines",      // optionnel
  "horaires": "07:00-22:00",   // optionnel ; fermé hors horaires
  "voisins": ["place", "boulangerie"]
}
```
Pas de grille ni de pathfinding : se déplacer d'un lieu à un autre prend 1 tick, quel que soit le lieu.

### 6.3 Habitant (fiche)
```json
{
  "id": "gerard",
  "nom": "Gérard Mouchel",
  "age": 61,
  "metier": "Boulanger",
  "domicile": "maison_gerard",
  "lieu_travail": "boulangerie",
  "description": "Texte libre de 3-5 phrases : physique, manière de parler, tics.",
  "traits": ["grincheux", "perfectionniste", "fier", "tendre en secret"],
  "big_five": { "ouverture": 25, "conscienciosite": 90, "extraversion": 30,
                "agreabilite": 20, "nevrosisme": 65 },
  "facon_de_parler": "Phrases courtes, bougonne, jamais de compliments directs.",
  "objectifs": ["Garder la réputation de la meilleure baguette du canton"],
  "secrets": [
    { "id": "s_gerard_dettes", "contenu": "...", "connu_de": [] }
  ],
  "routine": "Se lève à 4h30, boulangerie jusqu'à 13h, sieste, café le soir.",
  "relations": {
    "bernard": { "affinite": -30, "description": "Le trouve faux-jeton." }
  }
}
```
- `affinite` va de -100 à +100 et évolue après chaque interaction (§7.6).
- `connu_de` : la liste des habitants qui connaissent ce secret. Elle est mise à jour quand un secret est révélé dans une conversation (détecté lors du résumé de conversation, §7.5).

### 6.4 Souvenir (mémoire)
```json
{
  "id": "mem_000123",
  "habitant_id": "lea",
  "jour": 2, "heure": "18:30",
  "type": "observation",       // observation | conversation | reflexion | plan
  "contenu": "Gérard a refusé de me rendre la monnaie en souriant. Bizarre.",
  "importance": 4,             // 1 (banal) → 10 (bouleversant)
  "mots_cles": ["gérard", "boulangerie", "monnaie"],
  "derniere_consultation": "j2-18:30",
  "sources": ["evt_000456"]    // événements d'origine
}
```

### 6.5 Événement (le format le plus important du projet)
Tout ce qui se passe est un événement. C'est **la matière première du showrunner** : on logue large, y compris les pensées internes (le « confessionnal »).

```json
{
  "id": "evt_000456",
  "jour": 2, "heure": "18:30", "tick": 55,
  "type": "dialogue",
  "lieu": "boulangerie",
  "acteurs": ["lea", "gerard"],
  "temoins": ["thomas"],
  "contenu": "Léa : « Vous faites toujours la tête comme ça ? »",
  "pensee": "Elle me cherche, celle-là.",
  "details": { "conversation_id": "conv_0012", "tour": 3 },
  "visibilite": "public",
  "importance": 5,
  "tags": [],
  "intensite": null,
  "source": "simulation"
}
```
- `type` : `deplacement | action | dialogue | pensee | reflexion | plan | revelation | relation | intervention | systeme`.
- `visibilite` : `public` (vu par les témoins), `prive` (pensées, réflexions : seul le showrunner les voit).
- `tags` et `intensite` sont remplis plus tard par le dérusheur.
- `source` : `simulation | producteur`.

### 6.6 Conversation
`id`, `participants`, `lieu`, `debut`, `fin`, `tours` (liste d'event_ids), `resume_par_participant` (dict), `secrets_reveles` (liste), `deltas_affinite` (dict).

### 6.7 Arc narratif (showrunner)
```json
{
  "id": "arc_003",
  "titre": "La boulangerie à vendre",
  "type": "secret",            // conflit | romance | secret | ambition | mystere | comique
  "personnages": ["gerard", "bernard"],
  "statut": "montee",          // mise_en_place | montee | climax | resolu | abandonne
  "resume": "...",
  "evenements_cles": ["evt_000120", "evt_000456"],
  "tension": 6,                // 0-10
  "questions_ouvertes": ["Gérard va-t-il signer ?"],
  "derniere_maj": "j3"
}
```

### 6.8 Épisode
```json
{
  "numero": 1,
  "titre": "Pain perdu",
  "jours_couverts": [1, 2],
  "precedemment": null,
  "cold_open": { "...": "scène" },
  "scenes": [
    {
      "id": "sc_01",
      "lieu": "cafe",
      "moment": "j1-08:00",
      "personnages": ["ines", "lea"],
      "intention": "Présenter Léa comme une étrangère curieuse.",
      "didascalies": "...",
      "repliques": [
        { "perso": "ines", "texte": "...", "sources": ["evt_000012"] }
      ],
      "fidelite": "fidele"     // fidele | embelli | invente (rempli par le fact-checker)
    }
  ],
  "cliffhanger": "...",
  "arcs": ["arc_001", "arc_003"],
  "interventions_utilisees": [],
  "stats": { "appels_llm": 0, "tokens": 0 }
}
```

### 6.9 Intervention (producteur)
`id`, `jour`, `heure`, `type`, `cible(s)`, `contenu`, `objectif_narratif` (pourquoi le producteur la fait), `arc_vise`, `resultat` (rempli après coup : ce qui s'est réellement passé).

---

## 7. La ville : moteur de simulation

### 7.1 Boucle principale (pseudo-code)
```
pour chaque jour:
    pour chaque habitant: générer plan_du_jour (1 appel)
    pour chaque tick de 07:00 à 23:00:
        appliquer interventions programmées à ce tick
        pour chaque habitant (ordre aléatoire, seed fixe):
            si occupé (action longue en cours) ou endormi: continuer
            perception = qui est là, ce qui vient de se passer au lieu, événements publics
            souvenirs = memory.retrieve(habitant, requête = perception + plan)
            décision = LLM(habitant_decision, fiche + plan + souvenirs + perception)
            valider décision, exécuter l'action, loguer événement(s)
            si action == parler_a: lancer conversation (§7.5)
        si somme importance récente d'un habitant > seuil: réflexion (§7.4)
    nuit: résumé de la journée par habitant (souvenir type "plan" pour le lendemain)
    optionnel: lancer la salle d'écriture si un épisode est dû
```

### 7.2 Actions des habitants (outils)
La décision du LLM est un JSON :
```json
{
  "pensee": "monologue intérieur, 1-2 phrases, dans la voix du personnage",
  "action": "aller_a",
  "arguments": { "lieu": "cafe" },
  "duree_ticks": 1,
  "importance": 3
}
```
| Action | Arguments | Effet |
|---|---|---|
| `aller_a` | `lieu` | Déplacement (1 tick). Refusé si le lieu est privé et pas le sien sans invitation, ou fermé. |
| `parler_a` | `habitant`, `intention` | Lance une conversation si la cible est dans le même lieu. |
| `faire` | `activite`, `duree_ticks` (1-8) | Activité libre (« pétrir la pâte », « lire »). L'habitant est occupé pendant la durée, **sans appel LLM** : c'est le levier principal d'économie. |
| `observer` | — | Regarde autour de lui, crée un souvenir d'observation. |
| `rentrer_dormir` | — | Fin de journée anticipée pour cet habitant. |

Une action invalide (lieu inconnu, cible absente) n'est pas fatale : l'erreur est renvoyée au LLM **une fois** pour qu'il corrige, puis on bascule sur `observer`.

### 7.3 Mémoire et récupération
Score d'un souvenir pour une requête :
```
score = w_recence * recence + w_importance * importance_norm + w_pertinence * pertinence
recence      = decay ** heures_simulees_depuis_derniere_consultation   (decay = 0.995)
importance_norm = importance / 10
pertinence   = similarité(requête, souvenir)
```
- Poids par défaut : 1 / 1 / 1 (configurables).
- **Pertinence, V1** : similarité TF-IDF ou recouvrement de mots-clés en Python pur (pas de dépendance, pas d'appel API).
- **Pertinence, V2 (optionnel)** : embeddings via l'API (mis en cache dans SQLite).
- On renvoie les `top_k` souvenirs (défaut 8) et on met à jour leur `derniere_consultation`.
- L'**importance** est donnée par le LLM *dans le même appel* que la décision ou le résumé (pas d'appel dédié).

### 7.4 Réflexion
- Déclenchée quand la somme des importances des souvenirs depuis la dernière réflexion dépasse `seuil_reflexion` (défaut 30).
- Appel `habitant_reflexion` : à partir des 20 derniers souvenirs, produire 1 à 3 réflexions de haut niveau (« Je crois que Bernard me cache quelque chose »), chacune avec importance et sources.
- Les réflexions sont stockées comme souvenirs (`type: reflexion`) et loguées comme événements privés.
- **Ancrage de personnalité** : le prompt de réflexion rappelle les traits et défauts du personnage. Une réflexion ne peut pas contredire un trait sans un événement important qui le justifie.

### 7.5 Conversations
- Démarrées par `parler_a`. La cible accepte ou refuse selon sa personnalité (première réplique éventuellement sèche).
- Deux modes (config `dialogue.mode`) :
  - `tour_par_tour` : un appel par réplique, chaque locuteur avec sa propre mémoire. Plus fidèle, plus coûteux.
  - `scene_unique` : un appel qui génère toute la conversation à partir des deux fiches et de leurs souvenirs. Économe en quota.
- Maximum `dialogue.max_tours` répliques (défaut 6). Chaque réplique peut porter `"fin": true`.
- Les autres habitants présents sont **témoins** : la conversation leur est visible et entre dans leur perception.
- Après la conversation, un appel `habitant_resume_conversation` par participant (ou un appel commun) renvoie :
  - le souvenir à stocker (avec importance) ;
  - le delta d'affinité envers l'autre (-20 à +20) ;
  - les secrets révélés éventuels (ids).

### 7.6 Relations
L'affinité est mise à jour avec les deltas, bornée entre -100 et +100. Chaque changement de plus de 10 points génère un événement `relation` (utile pour le dérusheur).

### 7.7 Économie d'appels
- Actions longues (`faire` sur plusieurs ticks) : pas d'appel pendant la durée.
- Les habitants seuls au travail peuvent recevoir une décision « par défaut » issue de leur routine (config `skip_seul_au_travail`).
- La nuit est sautée, sauf si important
- Budget dur par exécution (`budget.max_appels`) : la simulation s'arrête proprement quand il est atteint.
- **Ordre de grandeur visé** : environ 150 appels par jour simulé avec 5 habitants (à mesurer et afficher par `rushes stats`).

---

## 8. La salle d'écriture (showrunner)

Elle se lance par la commande `rushes episode` ou automatiquement tous les `show.jours_par_episode` jours (défaut 2). Chaque étape est un appel (ou quelques appels) avec une entrée et une sortie validées.

### 8.1 Dérusheur
- **Entrée** : les événements non encore tagués, par lots (taille configurable) pour tenir dans le contexte.
- **Sortie** : pour chaque événement, `tags` (conflit, romance, secret, revelation, humiliation, alliance, mensonge, comique, banal…) et `intensite` (0-10).
- **Sortie supplémentaire** : un résumé de la journée en 10 lignes max (stocké, sert au résumé hiérarchique).

### 8.2 Showrunner (arcs)
- **Entrée** : résumés des jours, arcs existants, événements d'intensité ≥ 5, pensées privées marquantes.
- **Sortie** :
  - mise à jour des arcs (nouveaux, progression du statut, tension, questions ouvertes) ;
  - pour l'épisode : **intrigue A** (principale), **intrigue B** (secondaire), éventuellement un **running gag** ;
  - la liste des événements à garder.
- **Règles** : alterner les tensions (un épisode calme après un épisode intense est permis), éviter la « soupe dramatique », respecter le principe du fusil de Tchekhov (un secret mis en avant finit par compter).

### 8.3 Scénariste
- **Entrée** : le plan d'épisode, les événements retenus avec leurs dialogues réels, les fiches des personnages (façon de parler).
- **Sortie** : 4 à 8 scènes au format §6.8. Chaque réplique cite ses `sources` (event_ids).
- **Mode** (config `show.fidelite`) :
  - `documentaire` : uniquement ce qui s'est passé ; les répliques peuvent être resserrées mais pas inventées ;
  - `inspire` : le scénariste peut condenser, déplacer et embellir, mais le fact-checker le signale.

### 8.4 Monteur
- Ajoute : `precedemment` (si épisode > 1), `cold_open` (la scène la plus accrocheuse, éventuellement extraite du milieu), `cliffhanger`, `titre`.
- Réordonne les scènes pour le rythme.

### 8.5 Fact-checker
- Compare chaque scène à ses événements sources et remplit `fidelite` (`fidele | embelli | invente`) avec une justification courte.
- En mode `documentaire`, une scène `invente` est renvoyée au scénariste une fois, puis supprimée.

### 8.6 Export
- `data/episodes/ep01.json` (format §6.8) et `ep01.md` (script lisible : titre, scènes, didascalies en italique, répliques).

---

## 9. Couche LLM

```python
class LLMProvider(Protocol):
    def complete_json(
        self,
        prompt: str,
        schema: type[BaseModel],
        *,
        system: str | None = None,
        temperature: float = 0.8,
        tag: str = "",
    ) -> BaseModel: ...
```
- `openai_compat.py` : utilise le SDK `openai` avec `base_url` et une clé selon le fournisseur choisi dans la config. Demande une sortie JSON et valide avec pydantic.
- **Réparation** : si le JSON est invalide, renvoyer l'erreur de validation au modèle une fois, puis lever une exception claire.
- **Rate limiter** : jeton par jeton, `max_requetes_par_minute` dans la config ; backoff exponentiel sur les erreurs 429/5xx.
- **Budget** : compte appels et tokens par `tag` (ex. `decision`, `dialogue`, `derusheur`). Écrit dans SQLite. Plafond dur.
- **Journal** : chaque appel est logué (tag, durée, tokens, succès) dans une table `llm_calls`. Option `debug_prompts: true` pour stocker prompts et réponses complets.
- **Mock** (`mock.py`) : renvoie des réponses valides et déterministes (seedées) pour chaque schéma. **Toute la suite de tests doit passer avec le mock, sans réseau.**
- **Cache** optionnel (hash du prompt → réponse) pour rejouer une simulation sans dépenser de quota.
- Température : habitants 0.9, salle d'écriture 0.7, fact-checker 0.2 (configurable).

---

## 10. Le producteur

Un agent de la salle d'écriture qui peut **agir sur la ville**. Il ne contrôle jamais les pensées ni les décisions des habitants : il change leur **environnement** et regarde comment ils réagissent.

### 10.1 Outils
| Outil | Effet dans la simulation |
|---|---|
| `evenement_public(type, lieu, jour, heure, description)` | Fête, marché, orage, panne de courant, réunion municipale. Annoncé à tous via la perception à partir d'une heure donnée. |
| `lettre_anonyme(destinataire, contenu, jour, heure)` | L'habitant trouve une lettre : c'est un événement de sa perception avec une importance élevée. |
| `rumeur(origine_lieu, contenu)` | Une rumeur est entendue par les habitants présents au lieu donné. |
| `nouvel_arrivant(fiche)` | Ajoute un habitant (fiche générée, validée par le schéma §6.3). Maximum 1 par saison. |
| `rendez_vous_fortuit(a, b, lieu, jour, heure)` | Donne à A et à B une raison crédible d'aller au même lieu (course à faire, colis à récupérer). Ils restent libres d'y aller ou non. |

### 10.2 Quand intervenir
- Le producteur s'exécute après le showrunner (§8.2).
- Il reçoit les arcs, leur tension et les derniers résumés.
- Il intervient si la tension moyenne des arcs actifs est restée sous `producteur.seuil_ennui` (défaut 4) pendant `producteur.jours_avant_intervention` jours (défaut 2), ou si un arc est bloqué depuis longtemps.
- Il doit justifier chaque intervention : `objectif_narratif` et `arc_vise`.

### 10.3 Garde-fous
- Maximum `producteur.max_par_jour` interventions par jour (défaut 1) et `producteur.max_par_saison` (défaut 6).
- Aucune modification directe des fiches, des mémoires ou des relations.
- Toutes les interventions sont des événements `source: producteur`, visibles dans la page **Coulisses**.
- Après coup, le champ `resultat` de l'intervention est rempli : est-ce que ça a produit l'effet voulu ? (Excellent matériau d'analyse.)

---

## 11. Interface web

FastAPI + Jinja2 + JS vanilla, légère (doit tourner sur le vieux portable). Rafraîchissement par polling toutes les quelques secondes, pas de WebSocket au début.

| Page | Contenu |
|---|---|
| `/` **La ville** | Carte SVG simple avec les lieux en blocs et les habitants en pastilles (initiales + couleur). Heure simulée, derniers événements publics en fil. |
| `/habitant/{id}` | Fiche, lieu actuel, plan du jour, dernières pensées, réflexions, relations (barres d'affinité), secrets (marqués connus/inconnus). |
| `/saison` | Liste des épisodes : numéro, titre, résumé, arcs. |
| `/episode/{n}` | Le script mis en forme. Les répliques sont cliquables pour voir les événements sources. Badge de fidélité par scène. Lecteur audio quand il existe (phase 7). |
| `/coulisses` | Interventions du producteur avec objectif et résultat, arcs et courbe de tension, logs bruts filtrables (lieu, habitant, type, tag), statistiques d'appels LLM. |

API JSON associée : `/api/etat`, `/api/evenements?depuis=`, `/api/habitants/{id}`, `/api/episodes`, `/api/episodes/{n}`, `/api/arcs`, `/api/stats`.

---

## 12. CLI

```
python -m rushes init [--seed 42]          # crée la base à partir du casting
python -m rushes simulate --jours 2        # fait avancer la ville
python -m rushes episode                   # lance la salle d'écriture sur les jours non couverts
python -m rushes run --jours 6             # simulate + episode en alternance (mode nuit)
python -m rushes serve [--port 8000]       # interface web
python -m rushes stats                     # appels, tokens, coût estimé par tag
python -m rushes reset                     # efface data/
```
Option globale `--provider mock|gemini|groq` qui surcharge la config.

---

## 13. Feuille de route

Chaque phase se termine par : tests verts, `ruff` propre, commit, résumé, **arrêt pour validation**.

### Phase 0 — Fondations
Squelette du dépôt, `pyproject.toml`, config, modèles pydantic, stockage SQLite, couche LLM avec mock + rate limiter + budget, CLI `init` / `reset` / `stats`.
**Critère** : `pytest` passe sans réseau ; `rushes init` crée la base à partir du casting.

### Phase 1 — Deux habitants au café
Mémoire + récupération (TF-IDF), décision, conversation `tour_par_tour`, résumé de conversation, événements logués.
**Critère** : Léa et Inès passent une matinée au café. Le lendemain, elles se souviennent de leur conversation (vérifiable dans les logs). Fonctionne en mock et en réel.

### Phase 2 — Le village
Cinq habitants, tous les lieux, plans du jour, horloge complète, actions longues, témoins, nuit.
**Critère** : 2 jours simulés en réel sous ~300 appels ; `rushes stats` affiche la répartition.

### Phase 3 — Vie intérieure
Réflexion, relations qui évoluent, secrets et révélations.
**Critère** : au moins une réflexion pertinente par habitant et par jour ; les affinités bougent de façon cohérente avec les conversations.

### Phase 4 — Interface web (ville)
Pages `/`, `/habitant/{id}`, `/coulisses` (logs + stats).
**Critère** : on suit la simulation en direct dans le navigateur.

### Phase 5 — Premier épisode
Dérusheur, showrunner, scénariste, monteur, fact-checker, export JSON/Markdown, pages `/saison` et `/episode/{n}`.
**Critère** : `rushes run --jours 4` produit 2 épisodes lisibles, avec cold open et cliffhanger, et des répliques reliées à leurs sources.

### Phase 6 — Le producteur
Outils d'intervention, déclenchement par l'ennui, garde-fous, page Coulisses enrichie.
**Critère** : sur une saison de 6 épisodes, au moins une intervention a visiblement relancé un arc.

### Phase 7 — Fiction audio
Voix TTS par personnage + narrateur, assemblage ffmpeg, lecteur sur la page de l'épisode.

### Phase 8 — Épisode vidéo
Images par scène (avatars + fonds de lieux simples, ou API d'images), cartons-titres, voix, musique libre de droits, montage ffmpeg en épisode de ~2 minutes.

### Bonus
- Mesure de la dérive de personnalité (évaluer le Big Five observé vs fiche, au fil des jours).
- Embeddings pour la pertinence mémoire.
- Mode multijoueur : un ami « souffle » des idées à un habitant.

---

## 14. Prompts (brouillons)

Chaque prompt est un fichier dans `prompts/`, chargé et rempli avec `str.format` (ou un mini moteur de templates). Les placeholders sont entre accolades. Ce sont des **points de départ** à itérer.

### 14.1 `habitant_decision.md`
```
Tu es {nom}, {age} ans, {metier} à {nom_ville}. Tu n'es PAS un assistant : tu es un
personnage avec ses qualités et ses défauts, et tu les assumes. Tu peux être de mauvaise
humeur, mentir, éviter quelqu'un, garder un secret, changer d'avis.

# Qui tu es
{description}
Traits : {traits}
Façon de parler : {facon_de_parler}
Tes objectifs : {objectifs}
Tes secrets (personne ne doit les découvrir sans raison) : {secrets}
Ce que tu penses des autres : {relations}

# Ton plan pour aujourd'hui
{plan_du_jour}

# Tes souvenirs qui te reviennent
{souvenirs}

# Maintenant
Nous sommes le jour {jour}, il est {heure}. Tu es à {lieu} ({description_lieu}).
Présents : {presents}
Ce qui vient de se passer ici : {evenements_recents}
{evenements_speciaux}

# Ce que tu peux faire
{liste_actions}
Lieux : {liste_lieux}

Réponds UNIQUEMENT avec ce JSON :
{{"pensee": "...", "action": "...", "arguments": {{...}}, "duree_ticks": 1, "importance": 1}}
- "pensee" : ton monologue intérieur (1-2 phrases, avec ta voix).
- "importance" : à quel point ce moment compte pour toi, de 1 (banal) à 10 (bouleversant).
```

### 14.2 `habitant_dialogue.md` (mode tour par tour)
```
Tu es {nom}. {description_courte} Façon de parler : {facon_de_parler}
Tu parles avec {interlocuteur} à {lieu}. Ce que tu penses de lui/elle : {relation}
Tes souvenirs liés : {souvenirs}
Ton intention : {intention}
Témoins présents : {temoins}

Conversation jusqu'ici :
{historique}

Donne ta prochaine réplique. Reste dans ton personnage. N'expose pas tes secrets sans
raison, mais tu peux te trahir si l'émotion est forte. Réplique courte et naturelle (1 à
3 phrases). Pas de politesse excessive si ce n'est pas ton genre.

JSON : {{"pensee": "...", "replique": "...", "fin": false}}
```

### 14.3 `habitant_resume_conversation.md`
```
Tu es {nom}. Voici la conversation que tu viens d'avoir avec {interlocuteur} :
{conversation}

JSON :
{{"souvenir": "ce que tu retiens, à la première personne, 1-2 phrases",
  "importance": 1-10,
  "delta_affinite": -20 à +20,
  "secrets_appris": ["id ou description de ce que tu as appris de nouveau et de secret"]}}
```

### 14.4 `habitant_reflexion.md`
```
Tu es {nom}. Traits : {traits}. Défauts que tu gardes : {defauts}.
Voici tes souvenirs récents :
{souvenirs_numerotes}

Quelles 1 à 3 conclusions de fond en tires-tu sur ta vie, les autres, ce que tu veux ?
Reste fidèle à ta personnalité : tu ne deviens pas plus gentil ou plus sage sans raison
forte.

JSON : {{"reflexions": [{{"contenu": "...", "importance": 1-10, "sources": [numéros]}}]}}
```

### 14.5 `derusheur.md`
```
Tu es dérusheur pour une série télé tirée de la vie réelle d'un village. Pour chaque
événement ci-dessous, attribue des tags parmi : {liste_tags}, et une intensité
dramatique de 0 (rien à garder) à 10 (scène culte). Sois exigeant : la plupart des
événements sont banals.
Puis résume la journée en 10 lignes maximum, en pointant les fils narratifs.

Événements :
{evenements}

JSON : {{"evenements": [{{"id": "...", "tags": [...], "intensite": 0}}],
        "resume_journee": "..."}}
```

### 14.6 `showrunner_arcs.md`
```
Tu es le showrunner d'une comédie dramatique tout public tirée de la vie réelle du
village de {nom_ville}. Tu ne peux raconter que ce qui s'est passé.

Personnages : {fiches_courtes}
Résumés des jours précédents : {resumes}
Arcs en cours : {arcs}
Événements forts depuis le dernier épisode : {evenements_forts}
Pensées privées marquantes (le public les verra en « confessionnal ») : {pensees}
Épisodes précédents (titres + résumé) : {episodes}

1. Mets à jour les arcs (statut, tension 0-10, questions ouvertes) ; crée-en si besoin.
2. Choisis pour l'épisode {numero} une intrigue A, une intrigue B, et éventuellement un
   running gag. Varie le rythme par rapport à l'épisode précédent.
3. Liste les événements à garder.

JSON selon le schéma : {schema}
```

### 14.7 `scenariste.md`
```
Tu es scénariste. Écris l'épisode {numero} à partir de ce plan : {plan}
Événements retenus (avec dialogues réels) : {evenements}
Façon de parler des personnages : {voix}
Mode de fidélité : {fidelite}
- documentaire : tu peux resserrer les répliques, jamais inventer un fait.
- inspire : tu peux condenser et embellir, mais chaque réplique cite ses sources.

4 à 8 scènes. Didascalies brèves et visuelles. Chaque réplique a un champ "sources"
(ids d'événements). Les pensées privées peuvent devenir des apartés face caméra.

JSON selon le schéma : {schema}
```

### 14.8 `producteur.md`
```
Tu es le producteur de l'émission. Tu ne contrôles pas les habitants : tu peux seulement
modifier leur environnement avec tes outils, puis ils réagiront librement.
Arcs et tension : {arcs}
Résumés récents : {resumes}
Interventions passées et leur résultat : {interventions}
Outils : {outils}
Interdits : blessure grave, mort, crime violent, contenu inapproprié, modifier
directement les pensées ou souvenirs de quelqu'un.

Faut-il intervenir maintenant ? Si oui, choisis UNE intervention subtile et crédible
pour le village, explique son objectif narratif et l'arc visé. Sinon, explique pourquoi
tu laisses les choses suivre leur cours.

JSON : {{"intervenir": true, "outil": "...", "arguments": {{...}},
        "objectif_narratif": "...", "arc_vise": "..."}}
```

(`habitant_plan_jour.md`, `monteur.md` et `fact_checker.md` sont à écrire sur le même modèle.)

---

## 15. Casting initial

### 15.1 La ville : Vaudrecourt
Village fictif d'environ 800 habitants dans une vallée. Les élections municipales ont lieu dans trois mois. Une gazette satirique anonyme, *Le Corbeau de Vaudrecourt*, apparaît chaque semaine sur le panneau de la place et tout le monde la lit en faisant semblant de ne pas la lire.

### 15.2 Lieux (`casting/world.json`)
| id | Nom | Type | Notes |
|---|---|---|---|
| `place` | La place de l'Église | public | Panneau d'affichage (où paraît *Le Corbeau*). |
| `cafe` | Le Zinc | public | Café-tabac d'Inès, 07:00-22:00. |
| `boulangerie` | Boulangerie Mouchel | public | 06:30-13:00 et 16:00-19:00. |
| `mairie` | La mairie | public | 09:00-17:00. |
| `lavoir` | Le vieux lavoir | public | Au bord de la rivière, coin tranquille. Le terrain fait l'objet de convoitises. |
| `ecole` | L'école | public | 08:30-16:30 en semaine. |
| `maison_X` | Une maison par habitant | prive | |

### 15.3 Habitants (`casting/habitants/*.json`)

**Gérard Mouchel** (`gerard`), 61 ans, boulanger.
- Traits : grincheux, perfectionniste, fier, tendre en secret avec les enfants.
- Big Five : O 25 · C 90 · E 30 · A 20 · N 65.
- Façon de parler : phrases courtes, bougonne, ne fait jamais de compliment direct.
- Objectif : rester « la meilleure baguette du canton » ; prendre sa retraite sans perdre la face.
- Secret : il est endetté et a reçu une offre d'une chaîne de boulangeries industrielles. Il envisage de signer.
- Relations : Bernard -30 (le trouve faux-jeton) · Inès +40 (ils se chamaillent mais se respectent) · Léa -10 (méfiant envers les nouveaux) · Thomas +20 (le trouve paresseux mais l'aime bien).

**Léa Fontaine** (`lea`), 29 ans, institutrice fraîchement arrivée de Lyon.
- Traits : curieuse, bavarde, idéaliste, maladroite, un peu donneuse de leçons.
- Big Five : O 85 · C 55 · E 75 · A 70 · N 45.
- Façon de parler : beaucoup de questions, enthousiaste, références culturelles.
- Objectif : se faire accepter au village ; monter un ciné-club dans la salle des fêtes.
- Secret : elle a quitté son ancienne école après une dispute publique avec un parent d'élève qui a mal tourné (rien d'illégal, mais elle en a honte).
- Relations : Inès +30 · Thomas +25 (intriguée) · Bernard +15 (il a été charmant) · Gérard -5.

**Bernard Lacaze** (`bernard`), 54 ans, maire depuis deux mandats.
- Traits : charmeur, ambitieux, beau parleur, pas méchant mais prêt à arranger la vérité.
- Big Five : O 50 · C 60 · E 90 · A 45 · N 35.
- Façon de parler : chaleureux, appelle tout le monde par son prénom, promesses floues.
- Objectif : être réélu ; « moderniser » le village.
- Secret : il a promis le terrain du lavoir à un promoteur en échange d'un financement pour sa campagne.
- Relations : Gérard -10 (le juge ringard mais populaire) · Inès +10 (méfiance polie) · Thomas -40 (soupçonne qu'il est le Corbeau) · Léa +30 (une électrice à séduire).

**Inès Haddad** (`ines`), 34 ans, patronne du Zinc.
- Traits : observatrice, drôle, loyale, rancunière, sait tout sur tout le monde.
- Big Five : O 60 · C 70 · E 65 · A 50 · N 40.
- Façon de parler : piquante, humour pince-sans-rire, ne dit jamais tout ce qu'elle sait.
- Objectif : racheter les murs du café (elle est locataire) avant qu'ils soient vendus.
- Secret : elle sait que Gérard est endetté (elle a vu une lettre de la banque traîner sur le comptoir) et n'a rien dit.
- Relations : Thomas +10 (son ex, rupture il y a un an, sentiments ambigus) · Gérard +45 · Bernard -20 · Léa +20.

**Thomas Kervella** (`thomas`), 37 ans, jardinier municipal et musicien qui n'a jamais percé.
- Traits : rêveur, drôle, procrastinateur, idéaliste, évite les conflits en face.
- Big Five : O 90 · C 25 · E 45 · A 65 · N 55.
- Façon de parler : ironique, digresse, cite des chansons.
- Objectif : sauver le lavoir (son coin préféré) ; finir enfin son album.
- Secret : c'est lui qui écrit *Le Corbeau de Vaudrecourt*. Il travaille pour la mairie : s'il est découvert, il perd son poste.
- Relations : Inès +50 (n'a jamais tourné la page) · Bernard -50 · Léa +30 · Gérard +25.

### 15.4 Ressorts dramatiques prévus (à ne pas imposer : à laisser émerger)
- Le terrain du lavoir : Bernard (promoteur) contre Thomas (le sauver).
- Le Corbeau : Bernard le cherche ; Thomas risque son poste.
- La boulangerie : Gérard va-t-il vendre ? Inès sait déjà.
- Léa la nouvelle : alliée potentielle de tout le monde, et elle pose trop de questions.
- Inès et Thomas : histoire pas finie.
- L'élection : en toile de fond.

---

## 16. Configuration (`config.yaml`)

```yaml
seed: 42

llm:
  provider: mock            # mock | gemini | groq
  gemini:
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"   # à vérifier
    model: "A_RENSEIGNER"   # un modèle rapide de l'offre gratuite
    api_key_env: GEMINI_API_KEY
  groq:
    base_url: "https://api.groq.com/openai/v1"                             # à vérifier
    model: "A_RENSEIGNER"
    api_key_env: GROQ_API_KEY
  max_requetes_par_minute: 10
  temperature:
    habitant: 0.9
    ecriture: 0.7
    fact_checker: 0.2
  cache: true
  debug_prompts: false

budget:
  max_appels: 400           # par exécution

sim:
  minutes_par_tick: 30
  debut_journee: "07:00"
  fin_journee: "23:00"
  skip_seul_au_travail: true

memoire:
  top_k: 8
  decay: 0.995
  poids: { recence: 1.0, importance: 1.0, pertinence: 1.0 }
  pertinence: tfidf         # tfidf | embeddings
  seuil_reflexion: 30

dialogue:
  mode: tour_par_tour       # tour_par_tour | scene_unique
  max_tours: 6

show:
  jours_par_episode: 2
  fidelite: documentaire    # documentaire | inspire
  episodes_par_saison: 8
  intensite_min_retenue: 5

producteur:
  actif: false              # activé en phase 6
  seuil_ennui: 4
  jours_avant_intervention: 2
  max_par_jour: 1
  max_par_saison: 6

web:
  port: 8000
  polling_secondes: 3
```

---

## 17. Tests et qualité

- **Unitaires** : récupération mémoire (scores), validation des actions, bornage des affinités, calcul de la tension, parsing des sorties LLM, garde-fous du producteur.
- **Intégration (mock)** : `init` → `simulate --jours 1` → `episode` produit un épisode valide selon le schéma.
- **Déterminisme** : même seed + mock = mêmes événements.
- **Réel (manuel)** : un script `scripts/smoke_test.sh` lance une demi-journée avec le vrai fournisseur et affiche les stats.
- `ruff check` et `ruff format` sans erreur avant chaque commit.

---

## 18. Pièges connus et parades

| Piège | Parade |
|---|---|
| Tout le monde est trop gentil (ton assistant) | Prompts qui insistent sur les défauts ; traits négatifs explicites ; « tu n'es pas un assistant ». |
| Dérive de personnalité | Fiche rappelée à chaque décision ; réflexion contrainte par les traits ; mesure de la dérive en bonus. |
| Boucles (re-bonjour, mêmes conversations) | Souvenir « j'ai déjà parlé à X aujourd'hui de Y » fortement pondéré ; refus d'un `parler_a` vers la même personne dans les N ticks. |
| JSON invalide | Validation pydantic + une tentative de réparation + repli sur `observer`. |
| Contexte trop long | Résumé hiérarchique (jour → semaine) ; top_k souvenirs ; lots pour le dérusheur. |
| Quota gratuit épuisé | Rate limiter, budget dur, cache, actions longues, mode `scene_unique`. |
| Scénariste qui invente | Sources obligatoires par réplique + fact-checker + mode documentaire. |
| Soupe dramatique | Le dérusheur est exigeant ; le showrunner alterne le rythme. |
| Producteur trop interventionniste | Seuils d'ennui, quotas, justification obligatoire, résultats mesurés. |
