# Rushes

Une petite ville peuplée d'agents LLM vit sa vie. Une salle d'écriture d'agents la regarde et en fait une série. Spécification complète : [SPEC.md](SPEC.md).

## Installation

```
pip install -e ".[dev]"
cp .env.example .env   # clés API (phase 1)
```

## Commandes disponibles

```
python -m rushes init [--seed 42]   # crée data/rushes.sqlite à partir de casting/
python -m rushes stats              # appels et tokens LLM par tag
python -m rushes reset              # efface data/
pytest
ruff check . && ruff format .
```

Avancement : phase 0 (fondations). Les décisions prises hors spec sont dans [docs/DECISIONS.md](docs/DECISIONS.md).
