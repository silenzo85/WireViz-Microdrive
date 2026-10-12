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
BELKA_KROK = 9.0   # odstep startow galezi na belce rozgaleznej [mm]; 9*cos60 = 4,5 mm miedzy liniami
CTG_KATA = 0.577   # = ctg(60 st.): galaz boczna pod katem 60 st. od poziomu


@dataclass
class Ulozenie:
    poz: dict = field(default_factory=dict)     # wezel -> (x, y)
    trasy: dict = field(default_factory=dict)   # odcinek -> [(x, y), ...] od rodzica
    bloki: dict = field(default_factory=dict)   # zlacze -> (x, y, strona), lewy dolny rog
    bbox: list = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    korzen: str = ""
    krawedz: dict = field(default_factory=dict)  # odcinek -> (rodzic, dziecko)
    belki: dict = field(default_factory=dict)    # wezel -> (x, y0, y1) belki rozgaleznej


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
    for k, (x, y0, y1) in sub.belki.items():
        u.belki[k] = (x + dx, y0 + dy, y1 + dy)
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
        # 1) wysokosci: ciezkie dziecko na osi, boczne naprzemiennie w gore / w dol,
        #    kazde w swoim pasmie (pasma liczone tylko w pionie)
        subs = [rek(c, False) for c in ch]
        gora, dol = u.bbox[3], u.bbox[1]
        if subs:
            gora, dol = max(gora, subs[0].bbox[3]), min(dol, subs[0].bbox[1])
        wys_y, start = [0.0], [0.0]
        ku = kd = 0
        for i, sub in enumerate(subs[1:], 1):
            if i % 2 == 1:  # w gore
                ku += 1
                cy = gora + ODSTEP + OPIS_DY + OPIS_H - sub.bbox[1]
                gora = cy + sub.bbox[3]
                start.append(ku * BELKA_KROK)
            else:           # w dol
                kd += 1
                cy = dol - ODSTEP - sub.bbox[3]
                dol = cy + sub.bbox[1]
                start.append(-kd * BELKA_KROK)
            wys_y.append(cy)
        # 2) BELKA ROZGALEZNA: kazda galaz boczna startuje z WLASNEGO punktu belki
        #    (co BELKA_KROK) i idzie pod katem 60 st. Linie sa rownolegle z odstepem
        #    BELKA_KROK*cos(kat) - nie zlewaja sie (wczesniej: prawie pionowe z jednego
        #    punktu, nakladaly sie w jeden pas). Zawartosc kazdej galezi odsuwana tak,
        #    zeby linie dalszych galezi przechodzily PRZED nia.
        koniec = [abs(cy - s0) * CTG_KATA for cy, s0 in zip(wys_y, start)]

        def x_linii(j, y0, y1):
            """Najdalej w prawo, gdzie linia galezi j przechodzi przez pasmo [y0, y1]."""
            lo, hi = sorted((start[j], wys_y[j]))
            a, b = max(lo, y0), min(hi, y1)
            if a > b:
                return None
            yy = b if wys_y[j] > start[j] else a
            return abs(yy - start[j]) * CTG_KATA

        for i, (c, sub, cy) in enumerate(zip(ch, subs, wys_y)):
            oid, _ = krawedz[c]
            dl = max(S_MIN, dl_opisu(oid) + 12)
            potrzeba = koniec[i] + 4
            if i == 0 and n in u.bloki and ch and not czy_korzen:
                # zlacze w linii ma tabele NAD wezlem - ciag dalszy wiazki zaczyna sie
                # dopiero za nia (para zlaczy na ogonku: tabele nachodzily na siebie)
                bx, _by, _s = u.bloki[n]
                potrzeba = max(potrzeba, bx + bloki[n].w + 4)
            for j in range(1, len(subs)):
                if j != i:
                    xl = x_linii(j, cy + sub.bbox[1], cy + sub.bbox[3])
                    if xl is not None:
                        potrzeba = max(potrzeba, xl + 4)
            cx = max(koniec[i] + dl, potrzeba - sub.bbox[0])
            if i == 0:
                trasa = [(0.0, 0.0), (cx, 0.0)]
            else:
                trasa = [(0.0, start[i]), (koniec[i], cy), (cx, cy)]
            _wklej(u, sub, cx, cy)
            u.trasy[oid] = trasa
            u.krawedz[oid] = (n, c)
            _bb(u.bbox, 0.0, min(0.0, cy, start[i]), cx,
                max(0.0, cy, start[i]) + OPIS_DY + OPIS_H)
        if len(subs) > 1:
            u.belki[n] = (0.0, min(start), max(start))
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
        ul.belki.pop(n, None)  # po recznym przesunieciu galezie wychodza z punktu wezla
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
