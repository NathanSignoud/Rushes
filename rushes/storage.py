"""Stockage SQLite (une table `id, data JSON` par entité) + export JSONL des événements."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from rushes.models import (
    Arc,
    Conversation,
    Evenement,
    Habitant,
    Intervention,
    Lieu,
    Souvenir,
)

# Les épisodes vivent dans data/episodes/*.json (SPEC §8.6), pas en base.
TABLES: dict[type[BaseModel], str] = {
    Lieu: "lieux",
    Habitant: "habitants",
    Souvenir: "souvenirs",
    Evenement: "evenements",
    Conversation: "conversations",
    Arc: "arcs",
    Intervention: "interventions",
}

SCHEMA = "".join(
    f"CREATE TABLE IF NOT EXISTS {t} (id TEXT PRIMARY KEY, data TEXT NOT NULL);"
    for t in TABLES.values()
) + (
    "CREATE TABLE IF NOT EXISTS meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);"
    "CREATE TABLE IF NOT EXISTS llm_calls ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, moment TEXT NOT NULL, tag TEXT NOT NULL,"
    " duree_ms INTEGER NOT NULL, tokens INTEGER NOT NULL, succes INTEGER NOT NULL,"
    " prompt TEXT, reponse TEXT);"
)

M = TypeVar("M", bound=BaseModel)


class Storage:
    def __init__(self, path: Path):
        self.path = path
        self.jsonl = path.parent / "events.jsonl"
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # --- Entités ---

    def put(self, obj: BaseModel) -> None:
        with self.conn:
            self.conn.execute(
                f"INSERT OR REPLACE INTO {TABLES[type(obj)]} (id, data) VALUES (?, ?)",
                (obj.id, obj.model_dump_json()),
            )

    def get(self, model: type[M], id: str) -> M | None:
        row = self.conn.execute(f"SELECT data FROM {TABLES[model]} WHERE id = ?", (id,)).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def all(self, model: type[M]) -> list[M]:
        rows = self.conn.execute(f"SELECT data FROM {TABLES[model]} ORDER BY rowid")
        return [model.model_validate_json(r[0]) for r in rows]

    def add_event(self, evt: Evenement) -> None:
        self.put(evt)
        with self.jsonl.open("a", encoding="utf-8") as f:
            f.write(evt.model_dump_json() + "\n")

    # --- Méta ---

    def set_meta(self, cle: str, valeur: str) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (cle, valeur))

    def get_meta(self, cle: str) -> str | None:
        row = self.conn.execute("SELECT valeur FROM meta WHERE cle = ?", (cle,)).fetchone()
        return row[0] if row else None

    # --- Journal des appels LLM ---

    def log_llm_call(
        self,
        tag: str,
        duree_ms: int,
        tokens: int,
        succes: bool,
        prompt: str | None = None,
        reponse: str | None = None,
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO llm_calls (moment, tag, duree_ms, tokens, succes, prompt, reponse)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    tag,
                    duree_ms,
                    tokens,
                    succes,
                    prompt,
                    reponse,
                ),
            )

    def llm_stats(self) -> list[tuple[str, int, int, int, float]]:
        """(tag, appels, tokens, échecs, durée moyenne en ms) par tag."""
        return self.conn.execute(
            "SELECT tag, COUNT(*), SUM(tokens), SUM(NOT succes), AVG(duree_ms)"
            " FROM llm_calls GROUP BY tag ORDER BY COUNT(*) DESC"
        ).fetchall()
