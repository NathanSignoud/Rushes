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
python -m rushes simulate --jours 1 [--provider mock|gemini|groq]
        [--habitants lea,ines] [--depart cafe] [--fin 12:00]
python -m rushes stats              # appels et tokens LLM par tag
python -m rushes reset              # efface data/
pytest
ruff check . && ruff format .
```

Scénario de la phase 1 (Léa et Inès, deux matinées au café) :

```
python -m rushes reset && python -m rushes init
python -m rushes simulate --jours 2 --habitants lea,ines --depart cafe --fin 12:00 --provider groq
```

Avancement : phase 1 (deux habitantes au café). Les décisions prises hors spec sont dans [docs/DECISIONS.md](docs/DECISIONS.md).
