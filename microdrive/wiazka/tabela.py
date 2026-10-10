# -*- coding: utf-8 -*-
"""tabela.py - tabela z naglowkiem: pomiar szerokosci kolumn i rysowanie."""

from .kolor import kody_koloru, rgb
from .scena import dopasuj, szer_tekstu

WIERSZ = 5.0   # wysokosc wiersza [mm]
TXT = 2.5      # wysokosc tekstu [mm]
MARG = 1.2     # margines w komorce [mm]
PROBKA = 6.0   # szerokosc probki koloru [mm]
SZARY = (225, 225, 225)


def probka(sc, x, yc, kody, w=PROBKA, h=3.0):
    """Probka koloru zyly: baza + pasek przez srodek."""
    sc.wyp(x, yc - h / 2, w, h, rgb(kody[0]), "WH_KOLOR")
    if len(kody) > 1:
        sc.wyp(x, yc - h / 6, w, h / 3, rgb(kody[1]), "WH_KOLOR")
    sc.prost(x, yc - h / 2, w, h, "WH_KOLOR")


class Tabela:
    def __init__(self, tytul, naglowki, wiersze, kolory=(), max_kol=70.0, szerokosci=None):
        self.tytul = tytul or ""
        self.nagl = [str(n) for n in naglowki]
        self.wiersze = [[str(c) for c in w] for w in wiersze]
        self.kolory = set(kolory)  # indeksy kolumn z probka koloru
        if szerokosci:
            self.szer = list(szerokosci)
        else:
            self.szer = []
            for i, n in enumerate(self.nagl):
                s = max([szer_tekstu(n, TXT)] + [szer_tekstu(w[i], TXT) for w in self.wiersze])
                s += 2 * MARG + (PROBKA + MARG if i in self.kolory else 0)
                self.szer.append(min(s, max_kol))
        w_tyt = szer_tekstu(self.tytul, TXT) + 2 * MARG
        if w_tyt > sum(self.szer):
            self.szer[-1] += w_tyt - sum(self.szer)
        self.w = sum(self.szer)
        self.h_tyt = WIERSZ if self.tytul else 0.0
        self.h = self.h_tyt + WIERSZ * (len(self.wiersze) + 1)

    def rysuj(self, sc, x, y_top, warstwa="WH_TABELA"):
        y = y_top
        if self.tytul:
            sc.tekst(dopasuj(self.tytul, self.w - 2 * MARG, TXT), x + MARG, y - WIERSZ / 2,
                     TXT, "WH_OPIS")
            y -= WIERSZ
        y_siatki = y
        sc.wyp(x, y - WIERSZ, self.w, WIERSZ, SZARY, warstwa)
        self._wiersz(sc, x, y, self.nagl, naglowek=True)
        y -= WIERSZ
        for w in self.wiersze:
            self._wiersz(sc, x, y, w)
            y -= WIERSZ
        sc.prost(x, y, self.w, y_top - y, warstwa)
        yy = y_siatki
        while yy > y + 1e-6:
            sc.linia([(x, yy), (x + self.w, yy)], warstwa)
            yy -= WIERSZ
        xx = x
        for s in self.szer[:-1]:
            xx += s
            sc.linia([(xx, y_siatki), (xx, y)], warstwa)

    def _wiersz(self, sc, x, y_top, komorki, naglowek=False):
        yc = y_top - WIERSZ / 2
        for i, t in enumerate(komorki):
            s = self.szer[i]
            xt = x + MARG
            if i in self.kolory and not naglowek:
                kody = kody_koloru(t)
                if kody:
                    probka(sc, xt, yc, kody)
                    xt += PROBKA + MARG
            sc.tekst(dopasuj(t, x + s - MARG - xt, TXT), xt, yc, TXT, "WH_OPIS")
            x += s
