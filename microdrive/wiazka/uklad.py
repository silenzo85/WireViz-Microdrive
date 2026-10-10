# -*- coding: utf-8 -*-
"""
uklad.py - automatyczne rozmieszczenie drzewa wiazki (docs/54 rozdz. 5).

Rysunek BEZ SKALI: narysowana dlugosc odcinka sluzy czytelnosci, prawdziwa jest w opisie.
Wspolrzedne: korzen (zlacze z najwieksza liczba zyl) w (0, 0); te same wspolrzedne
uzywa uklad.csv do recznej korekty.

Zasada: "ciezkie" dziecko (najglebsze poddrzewo) idzie poziomo w prawo, pozostale
naprzemiennie w gore i w dol, kazde poddrzewo w swoim pasmie pionowym (pasma sie nie
nakladaja). Trasa do bocznego dziecka: z wezla prawie pionowo (rozne nachylenia, wiec
trasy sie nie pokrywaja), potem poziomo.
"""

from collections import Counter, deque
from dataclasses import dataclass, field

from .blok_zlacza import BlokZlacza
from .bom import naturalnie
from .scena import szer_tekstu

S_MIN = 40.0      # minimalna narysowana dlugosc odcinka [mm]
ODSTEP = 10.0     # odstep pionowy miedzy pasmami galezi [mm]
WEZEL_R = 6.0     # polowa obrysu wezla nie-zlacza [mm]
OPIS_H = 2.5      # wysokosc opisu odcinka [mm]
OPIS_DY = 3.5     # opis nad osia odcinka [mm]
ODSUNIECIE = 1.0  # blok zlacza od wezla [mm]


@dataclass
class Ulozenie:
    poz: dict = field(default_factory=dict)     # wezel -> (x, y)
    trasy: dict = field(default_factory=dict)   # odcinek -> [(x, y), ...] od rodzica
    bloki: dict = field(default_factory=dict)   # zlacze -> (x, y, strona), lewy dolny rog
    bbox: list = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    korzen: str = ""
    krawedz: dict = field(default_factory=dict)  # odcinek -> (rodzic, dziecko)


def opis_odcinka(d, o, n_zyl):
    dl = "TBD" if o.dlugosc is None else f"{o.dlugosc} mm"
    osl = f" [{','.join(o.oslony)}]" if o.oslony else ""
    return f"{dl}{osl}  {n_zyl} zyl"


def _bb(bb, x0, y0, x1, y1):
    bb[0], bb[1] = min(bb[0], x0), min(bb[1], y0)
    bb[2], bb[3] = max(bb[2], x1), max(bb[3], y1)


def _korzen(d, drzewo):
    konce = Counter()
    for z in d.zyly_wiazki(drzewo.wid):
        konce[z.od] += 1
        konce[z.do] += 1
    zlacza = [n for n in drzewo.wezly if d.wezly[n].typ == "ZLACZE"]
    kandydaci = zlacza or list(drzewo.wezly)
    return sorted(kandydaci, key=lambda n: (-konce[n], naturalnie(n)))[0]


def _ukorzen(drzewo, korzen):
    dzieci = {n: [] for n in drzewo.wezly}
    krawedz = {}
    widziane = {korzen}
    kolejka = deque([korzen])
    while kolejka:
        n = kolejka.popleft()
        for s, oid in sorted(drzewo.sas[n], key=lambda t: naturalnie(t[0])):
            if s not in widziane:
                widziane.add(s)
                dzieci[n].append(s)
                krawedz[s] = (oid, n)
                kolejka.append(s)
    return dzieci, krawedz


def _wysokosci(dzieci, korzen):
    wys = {}
    kolejnosc, stos = [], [korzen]
    while stos:
        n = stos.pop()
        kolejnosc.append(n)
        stos.extend(dzieci[n])
    for n in reversed(kolejnosc):
        wys[n] = 1 + max((wys[c] for c in dzieci[n]), default=-1)
    return wys


def _wklej(u, sub, dx, dy):
    for k, (x, y) in sub.poz.items():
        u.poz[k] = (x + dx, y + dy)
    for k, pts in sub.trasy.items():
        u.trasy[k] = [(x + dx, y + dy) for x, y in pts]
    for k, (x, y, s) in sub.bloki.items():
        u.bloki[k] = (x + dx, y + dy, s)
    u.krawedz.update(sub.krawedz)
    _bb(u.bbox, sub.bbox[0] + dx, sub.bbox[1] + dy, sub.bbox[2] + dx, sub.bbox[3] + dy)


def uloz(d, drzewo, zaw):
    bloki = {n: BlokZlacza(d, n) for n in drzewo.wezly if d.wezly[n].typ == "ZLACZE"}
    korzen = _korzen(d, drzewo)
    dzieci, krawedz = _ukorzen(drzewo, korzen)
    wys = _wysokosci(dzieci, korzen)

    def dl_opisu(oid):
        return szer_tekstu(opis_odcinka(d, d.odcinki[oid], len(zaw[oid])), OPIS_H)

    def rek(n, czy_korzen):
        u = Ulozenie()
        u.poz[n] = (0.0, 0.0)
        ch = sorted(dzieci[n], key=lambda c: (-wys[c], naturalnie(c)))
        if n in bloki:
            b = bloki[n]
            if czy_korzen:
                x, y, s = -ODSUNIECIE - b.w, -b.h / 2, -1
            elif not ch:
                x, y, s = ODSUNIECIE, -b.h / 2, 1
            else:  # zlacze w linii: blok nad wezlem
                x, y, s = -b.w / 2, WEZEL_R + 2, 1
            u.bloki[n] = (x, y, s)
            u.bbox = [x, y, x + b.w, y + b.h]
            _bb(u.bbox, -WEZEL_R, -WEZEL_R, WEZEL_R, WEZEL_R)
        else:
            u.bbox = [-WEZEL_R, -WEZEL_R, WEZEL_R, WEZEL_R]
        gora, dol = u.bbox[3], u.bbox[1]
        for i, c in enumerate(ch):
            oid, _ = krawedz[c]
            sub = rek(c, False)
            dl = max(S_MIN, dl_opisu(oid) + 12)
            if i == 0:
                cx = max(dl, 4 - sub.bbox[0])
                cy, t = 0.0, 0.0
                trasa = [(0.0, 0.0), (cx, 0.0)]
            else:
                if i % 2 == 1:  # w gore
                    cy = gora + ODSTEP + OPIS_DY + OPIS_H - sub.bbox[1]
                    zasieg = max(gora, 1.0)
                else:           # w dol
                    cy = dol - ODSTEP - sub.bbox[3]
                    zasieg = max(-dol, 1.0)
                # prawie pionowo: na wysokosci dotychczasowej zawartosci x = 1,5 mm
                t = max(2.0, 1.5 * abs(cy) / zasieg)
                cx = max(t + dl, t + 4 - sub.bbox[0])
                trasa = [(0.0, 0.0), (t, cy), (cx, cy)]
            _wklej(u, sub, cx, cy)
            u.trasy[oid] = trasa
            u.krawedz[oid] = (n, c)
            _bb(u.bbox, min(0.0, t), min(0.0, cy), cx, cy + OPIS_DY + OPIS_H)
            gora, dol = u.bbox[3], u.bbox[1]
        return u

    ul = rek(korzen, True)
    ul.korzen = korzen
    _nadpisz(d, ul, bloki)
    return ul


def _nadpisz(d, ul, bloki):
    """uklad.csv: przesun wezly; blok jedzie z wezlem, trasy przyleglych odcinkow od nowa."""
    ruszone = [n for n in d.uklad if n in ul.poz]
    if not ruszone:
        return
    for n in ruszone:
        x0, y0 = ul.poz[n]
        x1, y1 = d.uklad[n]
        ul.poz[n] = (x1, y1)
        if n in ul.bloki:
            bx, by, s = ul.bloki[n]
            ul.bloki[n] = (bx + x1 - x0, by + y1 - y0, s)
    for oid, (a, b) in ul.krawedz.items():
        if a in ruszone or b in ruszone:
            (xa, ya), (xb, yb) = ul.poz[a], ul.poz[b]
            ul.trasy[oid] = [(xa, ya), (xa, yb), (xb, yb)] if ya != yb else [(xa, ya), (xb, yb)]
    bb = [0.0, 0.0, 0.0, 0.0]
    for x, y in ul.poz.values():
        _bb(bb, x - WEZEL_R, y - WEZEL_R, x + WEZEL_R, y + WEZEL_R + OPIS_DY + OPIS_H)
    for n, (x, y, s) in ul.bloki.items():
        _bb(bb, x, y, x + bloki[n].w, y + bloki[n].h)
    for pts in ul.trasy.values():
        for x, y in pts:
            _bb(bb, x, y, x, y + OPIS_DY + OPIS_H)
    ul.bbox = bb
