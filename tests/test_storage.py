import json
from contextlib import closing

from rushes.models import Evenement, Souvenir
from rushes.storage import Storage


def evt(n: int) -> Evenement:
    return Evenement(
        id=f"evt_{n:06d}",
        jour=1,
        heure="08:00",
        tick=2,
        type="dialogue",
        lieu="cafe",
        acteurs=["lea", "ines"],
        contenu="Léa : « Vous servez des cafés crème ? »",
    )


def test_put_get_all(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        mem = Souvenir(
            id="mem_000001",
            habitant_id="lea",
            jour=1,
            heure="08:00",
            type="observation",
            contenu="Inès m'a souri.",
            importance=3,
            derniere_consultation="j1-08:00",
        )
        s.put(mem)
        s.put(mem.model_copy(update={"importance": 5}))  # remplace
        assert s.get(Souvenir, "mem_000001").importance == 5
        assert s.get(Souvenir, "absent") is None
        assert len(s.all(Souvenir)) == 1


def test_evenement_exporte_en_jsonl(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        s.add_event(evt(1))
        s.add_event(evt(2))
        assert [e.id for e in s.all(Evenement)] == ["evt_000001", "evt_000002"]
    lignes = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["id"] for line in lignes] == ["evt_000001", "evt_000002"]
    assert "« Vous servez" in lignes[0]  # UTF-8 lisible, pas d'échappement


def test_meta_et_stats(tmp_path):
    with closing(Storage(tmp_path / "db.sqlite")) as s:
        s.set_meta("seed", "42")
        assert s.get_meta("seed") == "42"
        assert s.get_meta("absent") is None
        s.log_llm_call("decision", 100, 50, True)
        s.log_llm_call("decision", 300, 70, False)
        s.log_llm_call("dialogue", 200, 10, True)
        assert s.llm_stats() == [("decision", 2, 120, 1, 200.0), ("dialogue", 1, 10, 0, 200.0)]
