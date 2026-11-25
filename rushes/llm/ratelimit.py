"""Limiteur de débit : seau à jetons de capacité 1 (une requête toutes les 60/rpm secondes)."""

import time
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self,
        max_par_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.intervalle = 60.0 / max_par_minute
        self.clock = clock
        self.sleep = sleep
        self.prochain: float | None = None

    def attendre(self) -> None:
        maintenant = self.clock()
        if self.prochain is not None and maintenant < self.prochain:
            self.sleep(self.prochain - maintenant)
            maintenant = self.prochain
        self.prochain = maintenant + self.intervalle
