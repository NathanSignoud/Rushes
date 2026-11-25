# Rushes

Simulation d'une petite ville peuplée d'agents LLM, plus une « salle d'écriture » d'agents qui transforme ce qui s'y passe en épisodes de série. Projet perso d'apprentissage de l'agentique.

**La spécification complète est dans `SPEC.md`. Lis-la avant toute tâche.**

## Règles du projet
- On avance **phase par phase** (SPEC §13). À la fin de chaque phase : tests verts, `ruff` propre, commit, résumé de ce qui a été fait, puis **stop** : attendre ma validation.
- **Aucun framework d'agents** (LangChain, LangGraph, CrewAI, AutoGen…). La boucle agentique est codée à la main : c'est le but du projet.
- Tout appel LLM passe par `rushes/llm/`. Toute sortie de LLM est validée par un schéma pydantic de `rushes/models.py`.
- Toute synthèse vocale passe par `rushes/tts/` (même principe : interface commune, moteurs interchangeables, moteur `mock`).
- La suite de tests doit passer **sans réseau ni téléchargement de modèle**, avec le fournisseur `mock` et le moteur TTS `mock`.
- Une seule machine : PC fixe Windows (i5-9400, 8 Go de RAM, GTX 1050 2 Go). Pas de LLM local. Le cœur reste léger ; les dépendances TTS sont optionnelles (extras `tts-light`, `tts-clone`), sur CPU par défaut. Un modèle de clonage ne tourne jamais en même temps que la simulation (verrou, SPEC §19.7).
- Windows d'abord, code compatible Linux : `pathlib`, ffmpeg appelé depuis le PATH, rien de propre à un OS dans le code.
- Voix : uniquement des extraits enregistrés avec consentement ou sous licence libre, jamais la voix d'une personne connue. Origine et licence dans `casting/voix/README.md`.
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
python -m rushes audio --episode 1 [--moteur piper]
python -m rushes serve [--host 0.0.0.0]
python -m rushes stats
pytest
ruff check . && ruff format .
scripts\nuit.bat 2 groq        # nuit complète : simulation + épisodes + audio
scripts\serveur.bat            # interface web sur le réseau local
```
