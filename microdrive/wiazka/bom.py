# -*- coding: utf-8 -*-
"""
bom.py - lista materialowa wiazki z policzonymi ilosciami (docs/54 rozdz. 3).

Ilosc nieznana (TODO / TBD po drodze) jest pokazywana jawnie, nie zgadywana.
"""

import re
from collections import Counter, OrderedDict
from dataclasses import dataclass

from .model import WEZLY_Z_CZESCIA

DLUGOSCIOWE = ("Przewod", "Kabel", "Oslona")


@dataclass
class Pozycja:
    typ: str
    producent: str
    pn: str
    opis: str
    ilosc: str


def naturalnie(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


class _Licznik:
    def __init__(self):
        self.p = OrderedDict()  # (typ, producent, pn, opis) -> int | None

    def dodaj(self, typ, prod, pn, opis, n):
        k = (typ, prod, pn, opis)
        stare = self.p.get(k, 0)
        self.p[k] = None if (stare is None or n is None) else stare + n

    def pozycje(self):
        wyn = []
        for (typ, prod, pn, opis), n in self.p.items():
            if typ in DLUGOSCIOWE:
                il = "TBD" if n is None else f"{n} mm"
            else:
                il = "TODO" if n is None else str(n)
            wyn.append(Pozycja(typ, prod, pn, opis, il))
        return wyn


def bom(d, drzewo, dlugosci):
    """dlugosci: ID zyly -> dlugosc ciecia (mm) albo None."""
    wid = drzewo.wid
    lic = _Licznik()
    zyly = sorted(d.zyly_wiazki(wid), key=lambda z: naturalnie(z.id))
    zajete = Counter()
    for z in zyly:
        for wz in (z.od, z.do):
            if wz in d.zlacza:
                zajete[wz] += 1

    for w in sorted(d.wezly_wiazki(wid), key=lambda w: naturalnie(w.id)):
        if w.typ == "ZLACZE":
            zl = d.zlacza[w.id]
            n = zajete[w.id]
            gn = zl.liczba_gniazd if zl.liczba_gniazd is not None else "TODO"
            lic.dodaj("Zlacze", zl.producent, zl.obudowa, f"{gn} gn.", 1)
            if zl.styk:
                lic.dodaj("Styk", zl.producent, zl.styk, "", n)
            if zl.uszczelka:
                lic.dodaj("Uszczelka", zl.producent, zl.uszczelka, "", n)
            if zl.zaslepka:
                wolne = None if zl.liczba_gniazd is None else zl.liczba_gniazd - n
                lic.dodaj("Zaslepka", zl.producent, zl.zaslepka, "", wolne)
            if zl.backshell:
                lic.dodaj("Backshell", zl.producent, zl.backshell, "", 1)
        elif w.typ in WEZLY_Z_CZESCIA:
            lic.dodaj(w.typ.capitalize(), w.producent, w.pn, w.opis, 1)

    luzem = [z for z in zyly if not z.kabel]
    for z in sorted(luzem, key=lambda z: (z.typ, z.przekroj, z.kolor)):
        lic.dodaj("Przewod", "", z.typ or "przewod", f"{z.przekroj} mm2 {z.kolor}",
                  dlugosci.get(z.id))

    for kid in sorted({z.kabel for z in zyly if z.kabel}, key=naturalnie):
        k = d.kable[kid]
        dl = [dlugosci.get(z.id) for z in zyly if z.kabel == kid]
        n = None if any(x is None for x in dl) else max(dl)
        ekran = ", ekran" if k.ekran else ""
        lic.dodaj("Kabel", k.producent, k.pn, f"{k.liczba_zyl} zyl{ekran}", n)

    for o in sorted(d.odcinki_wiazki(wid), key=lambda o: naturalnie(o.id)):
        for sid in o.oslony:
            s = d.oslony[sid]
            lic.dodaj("Oslona", s.producent, s.pn, f"{s.typ} {s.srednica} mm".strip(),
                      o.dlugosc)

    n_et = sum(1 for e in d.etykiety if e.wiazka == wid)
    if n_et:
        lic.dodaj("Etykieta", "", "", "etykieta wiazki", n_et)
    return lic.pozycje()
