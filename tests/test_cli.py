import shutil
from contextlib import closing

import pytest

from rushes.__main__ import main
from rushes.config import RACINE
from rushes.models import Habitant, Lieu
from rushes.storage import Storage


@pytest.fixture
def projet(tmp_path, monkeypatch):
    shutil.copytree(RACINE / "casting", tmp_path / "casting")
    shutil.copy(RACINE / "config.yaml", tmp_path / "config.yaml")
    monkeypatch.chdir(tmp_path)
    return tmp_path


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
