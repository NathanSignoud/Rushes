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
