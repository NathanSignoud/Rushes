"""CLI : python -m rushes <commande>."""

import argparse
import shutil
import sys
from contextlib import closing

from rushes.config import DATA_DIR, DB_NAME, charger_casting, charger_config
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
    sub.add_parser("reset", help="efface data/").set_defaults(func=cmd_reset)
    sub.add_parser("stats", help="appels et tokens LLM par tag").set_defaults(func=cmd_stats)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
