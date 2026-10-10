# -*- coding: utf-8 -*-
"""
topologia.py - drzewo wiazki: droga zyly, dlugosc ciecia, zawartosc odcinkow.

W drzewie droga miedzy dwoma wezlami jest jedyna, wiec przebiegu zyly sie nie wpisuje.
"""

from collections import deque


class Drzewo:
    def __init__(self, d, wid):
        self.wid = wid
        self.wezly = [w.id for w in d.wezly_wiazki(wid)]
        self.sas = {n: [] for n in self.wezly}  # wezel -> [(sasiad, id odcinka)]
        for o in d.odcinki_wiazki(wid):
            self.sas[o.a].append((o.b, o.id))
            self.sas[o.b].append((o.a, o.id))
        self._drogi = {}

    def droga(self, a, b):
        """ID odcinkow od a do b, w kolejnosci przejscia."""
        if a == b:
            return []
        if a not in self._drogi:
            prev = {a: None}
            kolejka = deque([a])
            while kolejka:
                n = kolejka.popleft()
                for s, oid in self.sas[n]:
                    if s not in prev:
                        prev[s] = (n, oid)
                        kolejka.append(s)
            self._drogi[a] = prev
        prev = self._drogi[a]
        if b not in prev:
            raise ValueError(f"brak drogi {a} -> {b} w wiazce {self.wid}")
        wynik, n = [], b
        while prev[n] is not None:
            n, oid = prev[n]
            wynik.append(oid)
        return wynik[::-1]


def naddatek_konca(d, wezel_id):
    zl = d.zlacza.get(wezel_id)
    if zl and zl.naddatek is not None:
        return zl.naddatek
    return d.naddatek_domyslny


def dlugosc_ciecia(d, drzewo, z):
    """Suma odcinkow drogi + naddatki na koncach + naddatek zyly; None, gdy po drodze TBD."""
    suma = 0
    for oid in drzewo.droga(z.od, z.do):
        dl = d.odcinki[oid].dlugosc
        if dl is None:
            return None
        suma += dl
    return suma + naddatek_konca(d, z.od) + naddatek_konca(d, z.do) + z.naddatek


def zawartosc(d, drzewo):
    """Odcinek -> lista ID zyl przez niego przechodzacych."""
    wyn = {o.id: [] for o in d.odcinki_wiazki(drzewo.wid)}
    for z in d.zyly_wiazki(drzewo.wid):
        for oid in drzewo.droga(z.od, z.do):
            wyn[oid].append(z.id)
    return wyn
