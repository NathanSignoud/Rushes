"""CLI : python -m rushes <commande>."""

import argparse
import shutil
import sys
from contextlib import closing

from rushes.config import DATA_DIR, DB_NAME, SimConfig, charger_casting, charger_config
from rushes.llm import creer_llm
from rushes.llm.base import LLMError
from rushes.llm.budget import BudgetEpuise
from rushes.sim.engine import simuler
from rushes.storage import Storage


def cmd_init(args: argparse.Namespace) -> int:
    db = DATA_DIR / DB_NAME
    if db.exists():
        print(f"La base {db} existe déjà. Lancez d'abord « python -m rushes reset ».")
        return 1
    seed = args.seed if args.seed is not None else charger_config().seed
    monde, habitants = charger_casting()
    DATA_DIR.mkdir(exist_ok=True)
    with closing(Storage(db)) as s:
        for obj in [*monde.lieux, *habitants]:
            s.put(obj)
        s.set_meta("seed", str(seed))
        s.set_meta("nom_ville", monde.nom)
        s.set_meta("description_ville", monde.description)
    print(
        f"Base créée : {db} ({monde.nom}, {len(monde.lieux)} lieux, "
        f"{len(habitants)} habitants, seed {seed})."
    )
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
        print(f"{DATA_DIR}/ effacé.")
    else:
        print(f"Rien à effacer : {DATA_DIR}/ n'existe pas.")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    db = DATA_DIR / DB_NAME
    if not db.exists():
        print("Pas de base : lancez « python -m rushes init ».")
        return 1
    config = charger_config()
    if args.fin:
        config.sim = SimConfig.model_validate({**config.sim.model_dump(), "fin_journee": args.fin})
    with closing(Storage(db)) as s:
        try:
            llm = creer_llm(config, s, seed=int(s.get_meta("seed") or 0), provider=args.provider)
            simuler(
                s,
                llm,
                config,
                args.jours,
                habitants=args.habitants.split(",") if args.habitants else None,
                depart=args.depart,
            )
        except (LLMError, ValueError) as e:
            print(f"Erreur : {e}")
            return 1
        except BudgetEpuise as e:
            print(f"Arrêt propre : {e}")
        print(
            f"Fin de la simulation (prochain jour : {s.get_meta('prochain_jour')}). "
            f"Appels LLM : {llm.budget.appels}, tokens : {llm.budget.tokens}."
        )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    db = DATA_DIR / DB_NAME
    if not db.exists():
        print("Pas de base : lancez « python -m rushes init ».")
        return 1
    with closing(Storage(db)) as s:
        lignes = s.llm_stats()
    if not lignes:
        print("Aucun appel LLM enregistré.")
        return 0
    print(f"{'tag':<20}{'appels':>8}{'tokens':>10}{'échecs':>8}{'ms moy.':>9}")
    for tag, appels, tokens, echecs, duree in lignes:
        print(f"{tag or '-':<20}{appels:>8}{tokens:>10}{echecs:>8}{duree:>9.0f}")
    print(
        f"{'TOTAL':<20}{sum(r[1] for r in lignes):>8}{sum(r[2] for r in lignes):>10}"
        f"{sum(r[3] for r in lignes):>8}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rushes", description="Rushes : la ville et la série.")
    sub = parser.add_subparsers(dest="commande", required=True)
    p_init = sub.add_parser("init", help="crée la base à partir du casting")
    p_init.add_argument("--seed", type=int, help="surcharge la seed de config.yaml")
    p_init.set_defaults(func=cmd_init)
    p_sim = sub.add_parser("simulate", help="fait avancer la ville")
    p_sim.add_argument("--jours", type=int, default=1)
    p_sim.add_argument("--provider", choices=["mock", "gemini", "groq"], help="surcharge la config")
    p_sim.add_argument("--habitants", help="ids séparés par des virgules (défaut : tous)")
    p_sim.add_argument("--depart", help="lieu où tous commencent la journée (défaut : chez soi)")
    p_sim.add_argument("--fin", help="heure de fin de journée, ex. 12:00 (défaut : config)")
    p_sim.set_defaults(func=cmd_simulate)
    sub.add_parser("reset", help="efface data/").set_defaults(func=cmd_reset)
    sub.add_parser("stats", help="appels et tokens LLM par tag").set_defaults(func=cmd_stats)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
