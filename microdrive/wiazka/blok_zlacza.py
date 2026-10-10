# -*- coding: utf-8 -*-
"""
blok_zlacza.py - symbol zlacza + widok czola + tabela pinow.

Wspolny dla ukladu (rozmiar) i rysunku (rysowanie) - jedno zrodlo wymiarow.
Etap 1: widok czola = siatka gniazd z numerami (zajete wyroznione), nie geometria z karty.
"""

import math

from .bom import naturalnie
from .scena import dopasuj
from .tabela import Tabela

SYM_W, SYM_H = 10.0, 14.0   # symbol zlacza [mm]
KRATKA = 5.0                # pole gniazda w widoku czola [mm]
ODST = 3.0                  # odstep symbol / czolo / tabela [mm]
SZARY_SYM = (200, 200, 200)
ZAJETE = (190, 215, 240)


def _wiersz(gn, drugi, gn2, z, zl):
    dokad = f"{drugi}.{gn2}" if gn2 else drugi
    return [gn, dokad, z.id, z.kolor, z.przekroj, zl.styk, z.sygnal]


def wiersze_pinow(d, zl_id):
    """(gniazdo, dokad, zyla, kolor, przekroj, styk, sygnal), kolejnosc naturalna gniazd."""
    zl = d.zlacza[zl_id]
    w = []
    for z in d.zyly.values():
        if z.od == zl_id:
            w.append(_wiersz(z.od_gn, z.do, z.do_gn, z, zl))
        if z.do == zl_id:
            w.append(_wiersz(z.do_gn, z.od, z.od_gn, z, zl))
    return sorted(w, key=lambda r: naturalnie(r[0]))


class BlokZlacza:
    def __init__(self, d, zl_id):
        zl = d.zlacza[zl_id]
        self.id = zl_id
        self.wiersze = wiersze_pinow(d, zl_id)
        uzyte = [r[0] for r in self.wiersze]
        self.uzyte = set(uzyte)
        if zl.liczba_gniazd:
            self.gn = [str(i) for i in range(1, zl.liczba_gniazd + 1)]
            self.gn += sorted({g for g in uzyte if not g.isdigit()}, key=naturalnie)
        else:
            self.gn = sorted(self.uzyte, key=naturalnie)
        n = max(len(self.gn), 1)
        self.kol = max(1, math.ceil(math.sqrt(n)))
        self.rzedy = math.ceil(n / self.kol)
        self.czolo_w, self.czolo_h = self.kol * KRATKA, self.rzedy * KRATKA
        tytul = f"{zl_id}  {zl.urzadzenie}  {zl.producent} {zl.obudowa}".strip()
        self.tab = Tabela(tytul, ["Gn", "Dokad", "Zyla", "Kolor", "mm2", "Styk", "Sygnal"],
                          self.wiersze, kolory={3}, max_kol=45.0)
        self.w = SYM_W + ODST + self.czolo_w + ODST + self.tab.w
        self.h = max(SYM_H + 10, self.czolo_h + 6, self.tab.h)

    def rysuj(self, sc, x, y, strona):
        """(x, y) = lewy dolny rog bloku. strona +1: symbol po lewej (wezel z lewej),
        -1: symbol po prawej (wezel z prawej)."""
        yc = y + self.h / 2
        if strona >= 0:
            xs = x
            xc = x + SYM_W + ODST
            xt = xc + self.czolo_w + ODST
        else:
            xt = x
            xc = x + self.tab.w + ODST
            xs = xc + self.czolo_w + ODST
        sc.wyp(xs, yc - SYM_H / 2, SYM_W, SYM_H, SZARY_SYM, "WH_ZLACZE")
        sc.prost(xs, yc - SYM_H / 2, SYM_W, SYM_H, "WH_ZLACZE")
        sc.tekst(self.id, xs + SYM_W / 2, yc + SYM_H / 2 + 2.5, 3.0, "WH_OPIS", "C")
        y0 = yc + self.czolo_h / 2
        for i, g in enumerate(self.gn):
            r, c = divmod(i, self.kol)
            cx, cy = xc + c * KRATKA, y0 - (r + 1) * KRATKA
            if g in self.uzyte:
                sc.wyp(cx, cy, KRATKA, KRATKA, ZAJETE, "WH_ZLACZE")
            sc.prost(cx, cy, KRATKA, KRATKA, "WH_ZLACZE")
            sc.tekst(dopasuj(g, KRATKA - 0.6, 1.6), cx + KRATKA / 2, cy + KRATKA / 2, 1.6,
                     "WH_OPIS", "C")
        self.tab.rysuj(sc, xt, yc + self.tab.h / 2)
