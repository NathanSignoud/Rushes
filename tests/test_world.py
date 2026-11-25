from rushes.config import RACINE, charger_config
from rushes.models import Lieu
from rushes.sim.world import Horloge, est_ouvert


def test_horloge():
    h = Horloge(charger_config(RACINE / "config.yaml").sim)
    assert h.ticks_par_jour == 32  # 07:00 → 23:00 par pas de 30 min
    assert (h.heure(0), h.heure(31)) == ("07:00", "22:30")
    assert h.tick(2, 23) == 55  # l'exemple du SPEC §6.5 : jour 2, 18:30


def test_horaires_multiples():
    boulangerie = Lieu(
        id="b", nom="B", description="", type="public", horaires="06:30-13:00,16:00-19:00"
    )
    ouvert = {h: est_ouvert(boulangerie, h) for h in ("06:00", "12:59", "13:00", "16:00", "19:00")}
    assert ouvert == {"06:00": False, "12:59": True, "13:00": False, "16:00": True, "19:00": False}
    assert est_ouvert(Lieu(id="p", nom="P", description="", type="public"), "03:00")
