# Décisions non couvertes par la spec

Chaque fois : l'option la plus simple, notée ici.

## Phase 0

1. **`LLMProvider` est une classe de base, pas un `Protocol`.** La signature `complete_json` est celle du §9. Les fournisseurs n'implémentent que `_generate(messages, schema, temperature) -> (texte, tokens)`. Validation, réparation, budget, débit et journal sont codés une seule fois dans la base.
2. **Reporté en phase 1** (la phase 0 ne demande que mock + rate limiter + budget) : `openai_compat.py` (Gemini/Groq), lecture de `.env` (python-dotenv), option `--provider`, cache des réponses. Noms de modèles et `base_url` restent « A_RENSEIGNER / à vérifier » jusqu'à la vérification de la doc en phase 1.
3. **Rate limiter = seau à jetons de capacité 1** : au plus une requête toutes les `60 / max_requetes_par_minute` secondes, sans rafale. C'est le plus prudent pour les offres gratuites. Le backoff sur 429/5xx viendra avec `openai_compat` (le SDK `openai` a des retries intégrés, à vérifier).
4. **Budget** : plafond total en mémoire, par exécution. Le détail par tag est dans la table `llm_calls` (SQLite), agrégée par `rushes stats`. Un appel en erreur réseau compte dans le budget (évite de boucler sur des échecs).
5. **Journal `llm_calls`** : une ligne par appel API. `succes` = l'appel a abouti **et** le JSON est valide. Un appel réparé donne donc deux lignes (un échec, un succès). Le prompt de réparation est dans `prompts/reparation_json.md`.
6. **Stockage** : une table par entité, `(id, data JSON)`. Les filtres viendront avec `json_extract` si besoin. Les épisodes ne sont pas en base : ce sont les fichiers `data/episodes/epNN.json` (§8.6).
7. **Config** : seules les sections `seed`, `llm` et `budget` sont typées pour l'instant. Les autres le seront dans leur phase (en attendant, pydantic ignore les clés inconnues). `config.yaml` est complet, comme au §16.
8. **Chemins** : `config.yaml`, `casting/` et `data/` sont relatifs au dossier courant (on lance depuis la racine). `prompts/` est relatif au paquet.
9. **Horaires multiples** : plages séparées par des virgules (`"06:30-13:00,16:00-19:00"`). L'école est ouverte `08:30-16:30` tous les jours : la sim n'a pas encore de notion de semaine.
10. **Casting** : le lieu de travail de Thomas (jardinier municipal) est le `lavoir`. Le secret de Gérard a `connu_de: ["ines"]`, ce qui est cohérent avec le secret d'Inès.
11. **`init`** refuse d'écraser une base existante (il faut passer par `reset`). **`reset`** efface `data/` sans confirmation : c'est son rôle.
12. **`stats`** n'affiche pas de coût estimé : les offres gratuites coûtent 0 €. À ajouter si on passe à une offre payante.
13. **Mock générique** : il parcourt le JSON Schema du modèle demandé et respecte types, bornes, énumérations et `examples` (posés sur les champs à motif : heure, moment, horaires). Il utilise un seul générateur seedé : même seed et même séquence d'appels donnent les mêmes réponses.
14. **Schémas de sortie LLM** (décision, dialogue, résumé…) : ajoutés à `models.py` dans la phase qui les utilise. La phase 0 couvre le modèle de données du §6.
15. **`Evenement`** : `importance` vaut 1 par défaut (bornée 1-10), `visibilite` vaut `public` par défaut.

## Phase 1

1. **Fournisseurs vérifiés le 2026-11-25** dans la doc officielle ([Gemini OpenAI](https://ai.google.dev/gemini-api/docs/openai), [modèles Gemini](https://ai.google.dev/gemini-api/docs/models), [limites Gemini](https://ai.google.dev/gemini-api/docs/rate-limits), [Groq OpenAI](https://console.groq.com/docs/openai), [modèles Groq](https://console.groq.com/docs/models), [limites Groq](https://console.groq.com/docs/rate-limits)).
   - Gemini : `gemini-3.5-flash-lite` (stable, recommandé par Google pour les nouveaux projets). Les limites gratuites par modèle ne sont plus publiées : elles se lisent dans AI Studio.
   - Groq : `openai/gpt-oss-20b` (production). La table de limites que je déduis être celle de l'offre gratuite donne : 30 req/min, 1K req/jour, 8K tokens/min, 200K tokens/jour. À ~1 200 tokens par appel, 200K tokens/jour ≈ 160 appels : c'est juste pour la cible de la phase 2.
2. **Pas de `response_format`** : le mode JSON n'est documenté que chez Groq. On extrait le JSON de la réponse (du premier `{` au dernier `}`), puis la validation pydantic et la réparation font le reste. Cela vaut pour tous les fournisseurs.
3. **Retries** : SDK `openai` avec `max_retries=5` (backoff exponentiel intégré). Un 429 qui persiste devient `BudgetEpuise` : la simulation s'arrête proprement.
4. **`reasoning_effort` non envoyé** : la réflexion ne se désactive pas sur Gemini 3 et plus, et les valeurs admises varient selon le modèle. On garde le réglage par défaut.
5. **Options de `simulate`** : `--habitants`, `--depart` et `--fin` permettent le scénario de la phase 1 (Léa et Inès au café le matin) et des essais réels peu coûteux. `--provider` est une option de `simulate` (et des futures commandes qui appellent un LLM).
6. **Mock et décisions** : le schéma `Decision` passé au LLM porte dans son JSON Schema des exemples de décisions valides ici et maintenant (observer, faire, parler à chaque présent, aller sur la place). Le mock y pioche, ce qui produit des conversations sans réseau. Les vrais fournisseurs ne voient que le prompt.
7. **Anti-boucle** : une même paire ne peut pas se reparler avant 4 ticks (2 h).
8. **`faire` occupe déjà l'habitant** pendant `duree_ticks`, sans appel LLM. C'est anticipé de la phase 2, parce que ça économise des appels dès maintenant.
9. **Souvenirs** : chaque décision (sauf `parler_a`) donne un souvenir `observation` avec l'importance donnée par le LLM. Chaque conversation donne un souvenir `conversation` par participant, issu de son résumé. `mots_cles` = ids du lieu et des présents. Comme les accents sont retirés, la pertinence TF-IDF relie « Inès » à l'id `ines`.
10. **Plan du jour** : la routine en tient lieu jusqu'à la phase 2.
11. **Deltas d'affinité et secrets appris** : enregistrés dans la `Conversation`, appliqués en phase 3. Les secrets restent pour l'instant du texte libre.
12. **Perception** : les événements publics du lieu depuis le tick précédent (8 au plus), et les présents.
13. **Tick global** : `(jour - 1) × ticks_par_jour + i`, cohérent avec l'exemple du §6.5 (jour 2, 18:30 = tick 55).
14. **Journée interrompue** (budget atteint ou erreur) : elle compte comme simulée, pour ne pas dupliquer d'événements au prochain lancement.
15. **Lieux privés** : il n'existe pas encore d'invitation, donc on n'entre que chez soi.
16. **Témoins** : calculés et logués dans les événements. Leurs souvenirs viendront en phase 2.
17. **Config** : `memoire.pertinence` n'accepte que `tfidf` (les embeddings sont un bonus). `dialogue.mode` n'est pas lu : seul `tour_par_tour` existe. Le cache (`llm.cache`) est toujours reporté : il est optionnel dans la spec.
