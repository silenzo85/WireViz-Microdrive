# -*- coding: utf-8 -*-
"""python -m wiazka <katalog danych> -o <katalog wyjscia> [--wiazka ID]"""

import argparse
import sys

from .generuj import generuj


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m wiazka",
                                 description="Arkusze fizycznych wiazek (docs/54).")
    ap.add_argument("dane", help="katalog z tabelami CSV wiazek")
    ap.add_argument("-o", "--wyjscie", default="../rysunki/wiazki", help="katalog wyjscia")
    ap.add_argument("--wiazka", help="tylko ta wiazka")
    a = ap.parse_args(argv)
    d, gotowe = generuj(a.dane, a.wyjscie, a.wiazka)
    n = {p: sum(1 for x in d.problemy if x.poziom == p)
         for p in ("BLAD", "OSTRZEZENIE", "BRAK")}
    print(f"narysowane: {', '.join(gotowe) or 'brak'} | bledy {n['BLAD']}, "
          f"ostrzezenia {n['OSTRZEZENIE']}, braki {n['BRAK']} -> "
          f"{a.wyjscie}/RAPORT_wiazka.txt")
    return 1 if n["BLAD"] else 0


if __name__ == "__main__":
    sys.exit(main())
