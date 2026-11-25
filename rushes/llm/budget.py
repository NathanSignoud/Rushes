"""Plafond dur d'appels par exécution. Le détail par tag est dans la table llm_calls."""


class BudgetEpuise(Exception):
    pass


class Budget:
    def __init__(self, max_appels: int):
        self.max_appels = max_appels
        self.appels = 0
        self.tokens = 0

    def verifier(self) -> None:
        if self.appels >= self.max_appels:
            raise BudgetEpuise(f"Budget atteint : {self.appels}/{self.max_appels} appels LLM.")

    def enregistrer(self, tokens: int) -> None:
        self.appels += 1
        self.tokens += tokens
