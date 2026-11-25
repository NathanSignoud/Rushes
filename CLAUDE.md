# Rushes

Simulation d'une petite ville peuplée d'agents LLM, plus une « salle d'écriture » d'agents qui transforme ce qui s'y passe en épisodes de série. Projet perso d'apprentissage de l'agentique.

**La spécification complète est dans `SPEC.md`. Lis-la avant toute tâche.**

## Règles du projet
- On avance **phase par phase** (SPEC §13). À la fin de chaque phase : tests verts, `ruff` propre, commit, résumé de ce qui a été fait, puis **stop** : attendre ma validation.
- **Aucun framework d'agents** (LangChain, LangGraph, CrewAI, AutoGen…). La boucle agentique est codée à la main : c'est le but du projet.
- Tout appel LLM passe par `rushes/llm/`. Toute sortie de LLM est validée par un schéma pydantic de `rushes/models.py`.
- La suite de tests doit passer **sans réseau**, avec le fournisseur `mock`.
- Le projet doit rester léger : il tournera sur un vieux portable sans GPU. Pas de modèle local, pas de dépendance lourde.
- Clés API uniquement dans `.env` (jamais commité). Ne jamais afficher une clé dans les logs.
- Noms de modèles et limites des offres gratuites : vérifier la doc actuelle des fournisseurs, ne rien inventer.
- Décision non couverte par la spec : option la plus simple, notée dans `docs/DECISIONS.md`.

## Conventions
- Python 3.11+, typage partout, pydantic v2.
- Identifiants de code en anglais ; contenu généré, prompts, commentaires et docs en français.
- Prompts dans `prompts/*.md`, jamais en dur dans le code.
- Données générées dans `data/` (ignoré par git).

## Commandes
```
python -m rushes init --seed 42
python -m rushes simulate --jours 1 --provider mock
python -m rushes episode
python -m rushes serve
python -m rushes stats
pytest
ruff check . && ruff format .
```
