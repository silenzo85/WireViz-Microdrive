# -*- coding: utf-8 -*-
"""
rysuj.py - arkusz 1 (rysunek wiazki w stylu RapidHarness) i strony tabel (docs/54 rozdz. 5).

Teksty generowane przez program bez polskich znakow (spojnosc z reszta DXF projektu);
teksty z danych przechodza bez zmian.
"""

import datetime
import math

from .blok_zlacza import BlokZlacza, wiersze_pinow
from .bom import naturalnie
from .scena import Scena, dopasuj, szer_tekstu
from .tabela import WIERSZ, Tabela
from .uklad import OPIS_DY, OPIS_H, opis_odcinka

FORMATY = [("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0),
           ("A0", 1189.0, 841.0)]
MARGINES = 10.0     # ramka od krawedzi arkusza [mm]
WEWN = 6.0          # zawartosc od ramki [mm]
ODSTEP_TAB = 6.0    # odstep miedzy tabelami bocznymi [mm]
RURKA = 1.6         # polowa szerokosci rurki wiazki [mm]
TYTUL_W = 190.0     # szerokosc tabelki rysunkowej [mm]
BANER_H = 12.0      # pas na znak TBD nad rysunkiem [mm]
CZERWONY = (200, 0, 0)
POMARANCZ = (255, 170, 60)
ZIELONY = (170, 220, 170)


def wybierz_format(w, h, wymuszony="auto"):
    """Najmniejszy arkusz ISO poziomo, ktory miesci (w, h); 'A2' itp. = najmniejszy dozwolony."""
    nazwy = [f[0] for f in FORMATY]
    od = nazwy.index(wymuszony) if wymuszony in nazwy else 0
    for nazwa, fw, fh in FORMATY[od:]:
        if w <= fw and h <= fh:
            return nazwa, fw, fh
    return "ponad A0", max(w, 1189.0), max(h, 841.0)


# --- dane tabel (wspolne dla stron PDF i CSV) --------------------------------

def _koniec(wz, gn):
    return f"{wz}.{gn}" if gn else wz


def dane_tabel(d, wid, pozycje, dlugosci):
    """nazwa -> (naglowki, wiersze, kolumny z probka koloru)."""
    zyly = sorted(d.zyly_wiazki(wid), key=lambda z: naturalnie(z.id))

    def dl(z):
        v = dlugosci.get(z.id)
        return "TBD" if v is None else str(v)

    pol = [[_koniec(z.od, z.od_gn), _koniec(z.do, z.do_gn), z.id, z.kolor, z.przekroj,
            z.typ, z.kabel + (f":{z.zyla_kabla}" if z.zyla_kabla else ""), z.skret, dl(z),
            z.sygnal, z.uwagi] for z in zyly]
    ciecie = [[z.id, z.typ or (f"kabel {z.kabel}" if z.kabel else ""), z.przekroj, z.kolor,
               dl(z), _koniec(z.od, z.od_gn), _koniec(z.do, z.do_gn)]
              for z in sorted(zyly, key=lambda z: (z.typ, z.przekroj, z.kolor,
                                                   naturalnie(z.id)))]
    bom_w = [[i + 1, p.typ, p.producent, p.pn, p.opis, p.ilosc]
             for i, p in enumerate(pozycje)]
    piny = []
    for w in sorted(d.wezly_wiazki(wid), key=lambda w: naturalnie(w.id)):
        if w.typ == "ZLACZE":
            piny += [[w.id] + r for r in wiersze_pinow(d, w.id)]
    ety = [[e.tekst, e.wezel or e.odcinek] for e in d.etykiety if e.wiazka == wid]
    return {
        "polaczenia": (["Od", "Do", "Zyla", "Kolor", "mm2", "Typ przewodu", "Kabel",
                        "Skrecona z", "Dl. ciecia mm", "Sygnal", "Uwagi"], pol, {3}),
        "lista_ciecia": (["Zyla", "Typ przewodu", "mm2", "Kolor", "Dl. ciecia mm", "Od",
                          "Do"], ciecie, {3}),
        "bom": (["Poz", "Typ", "Producent", "Numer katalogowy", "Opis", "Ilosc"], bom_w,
                set()),
        "piny": (["Zlacze", "Gn", "Dokad", "Zyla", "Kolor", "mm2", "Styk", "Sygnal"], piny,
                 {4}),
        "etykiety": (["Tekst", "Miejsce"], ety, set()),
    }


# --- strony tabel ------------------------------------------------------------

STRONY = [("polaczenia", "TABELA POLACZEN"), ("lista_ciecia", "LISTA CIECIA"),
          ("bom", "LISTA MATERIALOW"), ("etykiety", "ETYKIETY")]


def strony(d, wid, tabele, meta):
    wz = d.wiazki[wid]
    plan = []
    for klucz, tytul in STRONY:
        nagl, wiersze, kolory = tabele[klucz]
        if not wiersze:
            continue
        pelna = Tabela(tytul, nagl, wiersze, kolory, max_kol=55.0)
        nazwa, fw, fh = wybierz_format(pelna.w + 2 * (MARGINES + WEWN), 0.0)
        na_strone = int((fh - 2 * (MARGINES + WEWN) - 20.0) / WIERSZ) - 2
        kawalki = [wiersze[i:i + na_strone] for i in range(0, len(wiersze), na_strone)]
        for k, kaw in enumerate(kawalki):
            t = Tabela(f"{tytul} ({k + 1}/{len(kawalki)})", nagl, kaw, kolory,
                       szerokosci=pelna.szer)
            plan.append((t, fw, fh))
    wszystkie = 1 + len(plan)
    wyn = []
    for i, (t, fw, fh) in enumerate(plan):
        sc = Scena(fw, fh)
        sc.prost(MARGINES, MARGINES, fw - 2 * MARGINES, fh - 2 * MARGINES, "WH_RAMKA")
        naglowek = f"{wz.id}  {wz.nazwa}  -  {wz.numer or '-'} rew. {wz.rewizja or '-'}"
        sc.tekst(dopasuj(naglowek, fw - 2 * (MARGINES + WEWN), 3.5), MARGINES + WEWN,
                 fh - MARGINES - WEWN - 2, 3.5, "WH_OPIS")
        t.rysuj(sc, MARGINES + WEWN, fh - MARGINES - WEWN - 8)
        stopka = f"{meta.get('firma', '')}  -  strona {i + 2}/{wszystkie}"
        sc.tekst(stopka, fw - MARGINES - WEWN, MARGINES + 4, 2.5, "WH_OPIS", "R")
        wyn.append(sc)
    return wyn


# --- arkusz 1 ------------------------------------------------------------------

def rownolegla(pts, dist):
    """Polilinia przesunieta o dist w lewo wzgledem kierunku (naroza ostre)."""
    p = [pts[0]]
    for q in pts[1:]:
        if math.hypot(q[0] - p[-1][0], q[1] - p[-1][1]) > 1e-9:
            p.append(q)
    if len(p) < 2:
        return list(p)

    def nrm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        dl = math.hypot(dx, dy)
        return -dy / dl, dx / dl

    wyn = []
    for i in range(len(p)):
        if i == 0:
            nx, ny = nrm(p[0], p[1])
            k = dist
        elif i == len(p) - 1:
            nx, ny = nrm(p[-2], p[-1])
            k = dist
        else:
            n1, n2 = nrm(p[i - 1], p[i]), nrm(p[i], p[i + 1])
            nx, ny = n1[0] + n2[0], n1[1] + n2[1]
            cos1 = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            k = dist / cos1 if cos1 > 1e-9 else dist
        wyn.append((p[i][0] + nx * k, p[i][1] + ny * k))
    return wyn


def _szesciokat(x, y, r):
    return [(x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i)))
            for i in range(6)]


def _tabelka(wz, meta, fmt, n_stron):
    wiersze = [("Tytul", wz.nazwa), ("Wiazka", wz.id), ("Numer rysunku", wz.numer or "-"),
               ("Rewizja", wz.rewizja or "-"), ("Projekt", meta.get("projekt", "")),
               ("Firma", meta.get("firma", "")),
               ("Rysowal / data", f"{meta.get('rysowal', '')} / "
                                  f"{datetime.date.today().isoformat()}"),
               ("Format / arkuszy", f"{fmt} / {n_stron}")]
    return Tabela("", ["TABELKA RYSUNKOWA", ""], wiersze, szerokosci=[38.0, TYTUL_W - 38.0])


def arkusz1(d, wid, ul, zaw, pozycje, meta, n_stron):
    wz = d.wiazki[wid]
    bloki = {n: BlokZlacza(d, n) for n in ul.bloki}
    boczne = []
    rw = [r for r in d.rewizje if r.wiazka == wid]
    if rw:
        boczne.append(Tabela("REWIZJE", ["Rew", "Data", "Autor", "Opis"],
                             [[r.rewizja, r.data, r.autor, r.opis] for r in rw], max_kol=90))
    uw = [u for u in d.uwagi if u.wiazka == wid]
    if uw:
        boczne.append(Tabela("UWAGI", ["Nr", "Tekst"], [[u.nr, u.tekst] for u in uw],
                             max_kol=150))
    osl = sorted({s for o in d.odcinki_wiazki(wid) for s in o.oslony}, key=naturalnie)
    if osl:
        boczne.append(Tabela("OSLONY", ["ID", "Typ", "Numer katalogowy", "Srednica mm",
                                        "Kolor"],
                             [[s, d.oslony[s].typ, d.oslony[s].pn, d.oslony[s].srednica,
                               d.oslony[s].kolor] for s in osl]))
    boczne.append(Tabela("LISTA MATERIALOW", ["Poz", "Typ", "Producent", "Numer katalogowy",
                                              "Opis", "Ilosc"],
                         [[i + 1, p.typ, p.producent, p.pn, p.opis, p.ilosc]
                          for i, p in enumerate(pozycje)], max_kol=55))

    x0, y0, x1, y1 = ul.bbox
    rys_w, rys_h = x1 - x0, y1 - y0 + BANER_H
    prawa_w = max([TYTUL_W] + [t.w for t in boczne])
    tyt_h = _tabelka(wz, meta, "A0", n_stron).h
    prawa_h = sum(t.h + ODSTEP_TAB for t in boczne) + tyt_h
    W = 2 * (MARGINES + WEWN) + rys_w + 2 * WEWN + prawa_w
    H = 2 * (MARGINES + WEWN) + max(rys_h, prawa_h)
    fmt, fw, fh = wybierz_format(W, H, d.parametry.get("format_arkusza", "auto"))
    sc = Scena(fw, fh)
    sc.prost(MARGINES, MARGINES, fw - 2 * MARGINES, fh - 2 * MARGINES, "WH_RAMKA")

    px = fw - MARGINES - WEWN - prawa_w
    y = fh - MARGINES - WEWN
    for t in boczne:
        t.rysuj(sc, px, y)
        y -= t.h + ODSTEP_TAB
    tyt = _tabelka(wz, meta, fmt, n_stron)
    tyt.rysuj(sc, fw - MARGINES - WEWN - TYTUL_W, MARGINES + WEWN + tyt.h)

    dx = MARGINES + WEWN - x0
    dy = fh - MARGINES - WEWN - BANER_H - y1
    if any(o.dlugosc is None for o in d.odcinki_wiazki(wid)):
        sc.tekst("DLUGOSCI NIEPOTWIERDZONE (TBD) - NIE DO PRODUKCJI", MARGINES + WEWN,
                 fh - MARGINES - WEWN - 4, 4.0, "WH_UWAGA", rgb=CZERWONY)
    _drzewo(sc, d, wid, ul, zaw, bloki, dx, dy)
    return sc


def _drzewo(sc, d, wid, ul, zaw, bloki, dx, dy):
    def P(p):
        return p[0] + dx, p[1] + dy

    for oid, trasa in ul.trasy.items():
        pts = [P(p) for p in trasa]
        for s in (RURKA, -RURKA):
            sc.linia(rownolegla(pts, s), "WH_WIAZKA")
        o = d.odcinki[oid]
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        sc.tekst(opis_odcinka(d, o, len(zaw[oid])), (ax + bx) / 2, ay + OPIS_DY + OPIS_H / 2,
                 OPIS_H, "WH_OPIS", "C", rgb=CZERWONY if o.dlugosc is None else None)

    for w in sorted(d.wezly_wiazki(wid), key=lambda w: naturalnie(w.id)):
        x, y = P(ul.poz[w.id])
        if w.typ == "ROZGALEZIENIE":
            sc.okrag(x, y, 2.2, "WH_WEZEL", wypelniony=True)
        elif w.typ == "SPLICE":
            pts = _szesciokat(x, y, 3.5)
            sc.wielokat(pts, ZIELONY, "WH_WEZEL")
            sc.linia(pts + [pts[0]], "WH_WEZEL")
            sc.tekst(w.id, x, y - 6.0, 2.5, "WH_OPIS", "C")
        elif w.typ == "PRZEPUST":
            sc.wyp(x - 1.5, y - 6.0, 3.0, 12.0, (60, 60, 60), "WH_WEZEL")
            sc.tekst(w.id, x, y - 8.5, 2.5, "WH_OPIS", "C")
        elif w.typ == "ELEMENT":
            sc.wyp(x - 7.0, y - 3.5, 14.0, 7.0, (255, 255, 255), "WH_WEZEL")
            sc.prost(x - 7.0, y - 3.5, 14.0, 7.0, "WH_WEZEL")
            sc.tekst(dopasuj(w.id, 13.0, 2.2), x, y, 2.2, "WH_OPIS", "C")
            sc.tekst(dopasuj(w.opis, 40.0, 2.0), x, y - 5.5, 2.0, "WH_OPIS", "C")
        elif w.typ == "ZLACZE":
            bx, by, s = ul.bloki[w.id]
            bloki[w.id].rysuj(sc, bx + dx, by + dy, s)

    for e in [e for e in d.etykiety if e.wiazka == wid]:
        if e.odcinek in ul.trasy:
            pts = [P(p) for p in ul.trasy[e.odcinek]]
            (ax, ay), (bx, by) = pts[-2], pts[-1]
            x, y = ax + (bx - ax) * 0.15, ay - 5.0
        elif e.wezel in ul.poz:
            x, y = P(ul.poz[e.wezel])
            # pod symbolem zlacza (ten siega 7 mm pod os), nie na nim
            x, y = x - 10.0, y - 12.0
        else:
            continue
        w_ = szer_tekstu(e.tekst, 2.2) + 3.0
        sc.wyp(x, y - 2.2, w_, 4.4, POMARANCZ, "WH_OPIS")
        sc.prost(x, y - 2.2, w_, 4.4, "WH_OPIS")
        sc.tekst(e.tekst, x + 1.5, y, 2.2, "WH_OPIS")

    licznik = {}
    for u in [u for u in d.uwagi if u.wiazka == wid]:
        for n in u.wezly:
            if n not in ul.poz:
                continue
            k = licznik.get(n, 0)
            licznik[n] = k + 1
            x, y = P(ul.poz[n])
            # nad opisem odcinka (ten konczy sie ~6 mm nad osia), nie na nim
            cx, cy = x - 4.0 - 7.0 * k, y + 12.0
            sc.okrag(cx, cy, 2.8, "WH_UWAGA", rgb=(230, 180, 0), wypelniony=True)
            sc.okrag(cx, cy, 2.8, "WH_UWAGA")
            sc.tekst(u.nr, cx, cy, 2.5, "WH_OPIS", "C")
