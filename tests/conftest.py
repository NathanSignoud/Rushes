import shutil

import pytest

from rushes.config import RACINE


@pytest.fixture
def projet(tmp_path, monkeypatch):
    """Un dossier de projet jetable (casting + config) comme dossier courant."""
    shutil.copytree(RACINE / "casting", tmp_path / "casting")
    shutil.copy(RACINE / "config.yaml", tmp_path / "config.yaml")
    monkeypatch.chdir(tmp_path)
    return tmp_path
