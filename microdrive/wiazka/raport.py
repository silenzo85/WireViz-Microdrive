# -*- coding: utf-8 -*-
"""raport.py - RAPORT_wiazka.txt: bledy, ostrzezenia, brakujace dane, co narysowano."""

from pathlib import Path

SEKCJE = (("BLAD", "BLEDY - wiazka z bledem NIE zostala narysowana"),
          ("OSTRZEZENIE", "OSTRZEZENIA"),
          ("BRAK", "BRAKUJACE DANE (TODO / TBD) - widoczne na rysunku"))


def raport(d, sciezka, narysowane):
    linie = ["RAPORT GENERATORA ARKUSZY WIAZEK (docs/54)", "=" * 78, ""]
    for poziom, tytul in SEKCJE:
        p = [x for x in d.problemy if x.poziom == poziom]
        linie.append(f"{tytul}: {len(p)}")
        for x in p:
            wz = f"[{x.wiazka}] " if x.wiazka else ""
            linie.append(f"  {x.zrodlo:26s} {wz}{x.tekst}")
        linie.append("")
    linie.append("NARYSOWANE: " + (", ".join(narysowane) or "brak"))
    tekst = "\n".join(linie) + "\n"
    Path(sciezka).write_text(tekst, encoding="utf-8")
    return tekst
