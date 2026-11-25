import shutil
from contextlib import closing

from rushes.__main__ import main
from rushes.config import RACINE
from rushes.models import Evenement, Habitant, Lieu
from rushes.storage import Storage


def test_init_stats_reset(projet, capsys):
    assert main(["init", "--seed", "7"]) == 0
    db = projet / "data" / "rushes.sqlite"
    with closing(Storage(db)) as s:
        assert len(s.all(Habitant)) == 5
        assert len(s.all(Lieu)) == 11
        assert s.get(Habitant, "gerard").secrets[0].connu_de == ["ines"]
        assert s.get_meta("seed") == "7"
        assert s.get_meta("nom_ville") == "Vaudrecourt"

    assert main(["init"]) == 1  # ne pas écraser une base existante

    assert main(["stats"]) == 0
    assert "Aucun appel LLM" in capsys.readouterr().out

    assert main(["reset"]) == 0
    assert not (projet / "data").exists()


def test_init_seed_par_defaut(projet):
    assert main(["init"]) == 0
    with closing(Storage(projet / "data" / "rushes.sqlite")) as s:
        assert s.get_meta("seed") == "42"


def simuler_dans(dossier, monkeypatch) -> list[tuple]:
    shutil.copytree(RACINE / "casting", dossier / "casting")
    shutil.copy(RACINE / "config.yaml", dossier)
    monkeypatch.chdir(dossier)
    assert main(["init", "--seed", "3"]) == 0
    args = ["simulate", "--jours", "2", "--fin", "10:00", "--provider", "mock"]
    assert main([*args, "--habitants", "lea,ines", "--depart", "cafe"]) == 0
    with closing(Storage(dossier / "data" / "rushes.sqlite")) as s:
        assert s.get_meta("prochain_jour") == "3"
        return [(e.tick, e.type, e.contenu, e.pensee) for e in s.all(Evenement)]


def test_simulation_mock_deterministe(tmp_path, monkeypatch):
    a = simuler_dans(tmp_path / "a", monkeypatch)
    assert any(type_ == "dialogue" for _, type_, _, _ in a)  # le mock fait parler les habitants
    assert a == simuler_dans(tmp_path / "b", monkeypatch)  # même seed + mock = mêmes événements
