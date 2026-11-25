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

Avancement : phase 1 (deux habitantes au café).

## Une seule machine

Tout tourne sur un PC fixe Windows (i5-9400, 8 Go de RAM, GTX 1050 2 Go). Les LLM passent par API. Les voix (phase 6) sont synthétisées en local, sur CPU, jamais en même temps que la simulation. Le code reste compatible Linux, avec WSL2 en plan B.

ffmpeg doit être dans le PATH à partir de la phase 6 (`winget install Gyan.FFmpeg`, puis rouvrir le terminal).

### Scripts (double-clic ou terminal)

```
scripts\nuit.bat [jours] [provider]   # simulation, puis épisodes, puis voix des nouveaux épisodes
scripts\serveur.bat [port]            # interface web ouverte au réseau local
```

Les scripts utilisent `.venv` s'il existe. Une étape qui n'existe pas encore (phase pas atteinte) est sautée avec un message.

### Ouvrir la page depuis un téléphone

1. Le téléphone et le PC sont sur le **même Wi-Fi**.
2. Sur le PC, lancer `scripts\serveur.bat`. Il affiche l'adresse à utiliser, par exemple `http://192.168.1.20:8000`. Sinon, `ipconfig` donne l'« Adresse IPv4 ».
3. Au premier lancement, Windows demande d'autoriser Python dans le pare-feu : cocher **Réseaux privés** seulement.
4. Sur le téléphone, ouvrir cette adresse dans le navigateur.

Le serveur n'a pas de mot de passe : à utiliser seulement sur le réseau de la maison, jamais sur un Wi-Fi public, et sans ouvrir le port sur la box. Lancé sans le script (`python -m rushes serve`), il n'écoute que le PC lui-même. Les décisions prises hors spec sont dans [docs/DECISIONS.md](docs/DECISIONS.md).
