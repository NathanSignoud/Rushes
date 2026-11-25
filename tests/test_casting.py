import json
import shutil

import pytest

from rushes.config import CASTING_DIR, RACINE, charger_casting, charger_config


def test_casting_complet_et_coherent():
    monde, habitants = charger_casting(RACINE / CASTING_DIR)
    assert monde.nom == "Vaudrecourt"
    assert {h.id for h in habitants} == {"gerard", "lea", "bernard", "ines", "thomas"}
    assert len(monde.lieux) == 11
    for h in habitants:  # chacun a un avis sur tous les autres
        assert set(h.relations) == {"gerard", "lea", "bernard", "ines", "thomas"} - {h.id}


def test_casting_reference_inconnue_refusee(tmp_path):
    shutil.copytree(RACINE / CASTING_DIR, tmp_path / "casting")
    fiche = tmp_path / "casting" / "habitants" / "lea.json"
    data = json.loads(fiche.read_text(encoding="utf-8"))
    data["domicile"] = "chateau"
    data["relations"]["fantome"] = {"affinite": 0, "description": "?"}
    fiche.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="domicile inconnu chateau") as exc:
        charger_casting(tmp_path / "casting")
    assert "relation vers un inconnu fantome" in str(exc.value)


def test_affinite_bornee(tmp_path):
    shutil.copytree(RACINE / CASTING_DIR, tmp_path / "casting")
    fiche = tmp_path / "casting" / "habitants" / "lea.json"
    data = json.loads(fiche.read_text(encoding="utf-8"))
    data["relations"]["ines"]["affinite"] = 150
    fiche.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="affinite"):
        charger_casting(tmp_path / "casting")


def test_config_chargee():
    config = charger_config(RACINE / "config.yaml")
    assert config.seed == 42
    assert config.llm.provider == "mock"
    assert config.budget.max_appels == 400
