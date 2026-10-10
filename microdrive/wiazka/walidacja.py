# -*- coding: utf-8 -*-
"""
walidacja.py - kontrole znaczeniowe danych wiazki (docs/54 rozdz. 4).

BLAD przerywa rysowanie wiazki, OSTRZEZENIE nie. Brakujace dane (TODO/TBD)
zbiera juz dane.py.
"""

from .kolor import kody_koloru
from .model import BRAKI, KONCE_ZYL, TYPY_WEZLOW, WEZLY_Z_CZESCIA


def waliduj(d):
    _wezly(d)
    _odcinki(d)
    _drzewa(d)
    _zyly(d)
    _dodatki(d)


def _wiazka_wezla(d, wid):
    w = d.wezly.get(wid)
    return w.wiazka if w else None


def _wezly(d):
    for w in d.wezly.values():
        if w.wiazka not in d.wiazki:
            d.dodaj("BLAD", w.zrodlo, f"wezel {w.id}: nieznana wiazka '{w.wiazka}'")
        if w.typ not in TYPY_WEZLOW:
            d.dodaj("BLAD", w.zrodlo, f"wezel {w.id}: nieznany typ '{w.typ}' "
                    f"(dozwolone: {', '.join(TYPY_WEZLOW)})", w.wiazka)
        if w.typ in WEZLY_Z_CZESCIA and not w.pn:
            d.dodaj("BLAD", w.zrodlo, f"wezel {w.id} ({w.typ}): wymagany Numer katalogowy "
                    "(jesli nieznany - wpisz TODO)", w.wiazka)
        if w.typ == "ZLACZE" and w.id not in d.zlacza:
            d.dodaj("BLAD", w.zrodlo, f"zlacze {w.id}: brak wiersza w zlacza.csv", w.wiazka)
    for z in d.zlacza.values():
        w = d.wezly.get(z.oznaczenie)
        if w is None or w.typ != "ZLACZE":
            d.dodaj("BLAD", z.zrodlo, f"zlacze {z.oznaczenie}: brak wezla typu ZLACZE "
                    "w wezly.csv", w.wiazka if w else None)


def _odcinki(d):
    for o in d.odcinki.values():
        if o.wiazka not in d.wiazki:
            d.dodaj("BLAD", o.zrodlo, f"odcinek {o.id}: nieznana wiazka '{o.wiazka}'")
            continue
        if o.a == o.b:
            d.dodaj("BLAD", o.zrodlo, f"odcinek {o.id}: oba konce w tym samym wezle", o.wiazka)
        for k in (o.a, o.b):
            w = d.wezly.get(k)
            if w is None:
                d.dodaj("BLAD", o.zrodlo, f"odcinek {o.id}: nieznany wezel '{k}'", o.wiazka)
            elif w.wiazka != o.wiazka:
                d.dodaj("BLAD", o.zrodlo, f"odcinek {o.id}: wezel {k} nalezy do wiazki "
                        f"{w.wiazka}, nie {o.wiazka}", o.wiazka)
        for s in o.oslony:
            if s not in d.oslony:
                d.dodaj("BLAD", o.zrodlo, f"odcinek {o.id}: nieznana oslona '{s}'", o.wiazka)


def _drzewa(d):
    for wid, wz in d.wiazki.items():
        wezly = [w.id for w in d.wezly_wiazki(wid)]
        if not wezly:
            d.dodaj("BLAD", wz.zrodlo, f"wiazka {wid}: brak wezlow", wid)
            continue
        rodzic = {n: n for n in wezly}

        def korzen(n):
            while rodzic[n] != n:
                rodzic[n] = rodzic[rodzic[n]]
                n = rodzic[n]
            return n

        for o in d.odcinki_wiazki(wid):
            if o.a not in rodzic or o.b not in rodzic or o.a == o.b:
                continue  # zgloszone w _odcinki
            ka, kb = korzen(o.a), korzen(o.b)
            if ka == kb:
                d.dodaj("BLAD", o.zrodlo, f"wiazka {wid}: odcinek {o.id} zamyka petle "
                        f"({o.a} - {o.b}); wiazka musi byc drzewem", wid)
            else:
                rodzic[ka] = kb
        czesci = {}
        for n in wezly:
            czesci.setdefault(korzen(n), []).append(n)
        if len(czesci) > 1:
            opis = "; ".join(", ".join(sorted(c)[:4]) for c in czesci.values())
            d.dodaj("BLAD", wz.zrodlo, f"wiazka {wid}: drzewo niespojne, {len(czesci)} "
                    f"oddzielne czesci: {opis}", wid)


def _zyly(d):
    zajete, konce = {}, set()
    for z in d.zyly.values():
        wid = _wiazka_wezla(d, z.od) or _wiazka_wezla(d, z.do)
        for strona, wz, gn in (("Od", z.od, z.od_gn), ("Do", z.do, z.do_gn)):
            w = d.wezly.get(wz)
            if w is None:
                d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: {strona} - nieznany wezel '{wz}'", wid)
                continue
            konce.add(wz)
            if w.typ not in KONCE_ZYL:
                d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: {wz} jest typu {w.typ}; zyla konczy "
                        "sie tylko na ZLACZE, SPLICE albo ELEMENT", wid)
            elif w.typ == "SPLICE":
                if gn:
                    d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: splice {wz} nie ma gniazd - "
                            f"kolumna '{strona} gniazdo' ma byc pusta", wid)
            elif not gn:
                d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: brak '{strona} gniazdo' dla {wz}", wid)
            else:
                k = (wz, gn)
                if k in zajete:
                    d.dodaj("BLAD", z.zrodlo, f"gniazdo {wz}.{gn} zajete dwa razy: "
                            f"{zajete[k]} i {z.id}", wid)
                else:
                    zajete[k] = z.id
                zl = d.zlacza.get(wz)
                if (zl and zl.liczba_gniazd and gn.isdigit()
                        and not 1 <= int(gn) <= zl.liczba_gniazd):
                    d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: gniazdo {wz}.{gn} poza zakresem "
                            f"1..{zl.liczba_gniazd}", wid)
        wa, wb = _wiazka_wezla(d, z.od), _wiazka_wezla(d, z.do)
        if wa and wb and wa != wb:
            d.dodaj("BLAD", z.zrodlo, f"zyla {z.id} laczy dwie wiazki ({wa}, {wb}); przejscie "
                    "miedzy wiazkami idzie przez pare zlaczy", wid)
        if z.kabel and z.kabel not in d.kable:
            d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: nieznany kabel '{z.kabel}'", wid)
        if z.skret and z.skret not in d.zyly:
            d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: 'Skrecona z' - nieznana zyla "
                    f"'{z.skret}'", wid)
        if z.kolor not in BRAKI and kody_koloru(z.kolor) is None:
            d.dodaj("BLAD", z.zrodlo, f"zyla {z.id}: nieznany kolor '{z.kolor}' "
                    "(kody jak w WireViz, pasek po ukosniku: BN/WH)", wid)
    for w in d.wezly.values():
        if w.typ in KONCE_ZYL and w.id not in konce:
            d.dodaj("OSTRZEZENIE", w.zrodlo, f"{w.typ.lower()} {w.id}: zadna zyla tu "
                    "nie dochodzi", w.wiazka)


def _dodatki(d):
    for e in d.etykiety:
        if e.wiazka not in d.wiazki:
            d.dodaj("BLAD", e.zrodlo, f"etykieta '{e.tekst}': nieznana wiazka '{e.wiazka}'")
        elif bool(e.wezel) == bool(e.odcinek):
            d.dodaj("BLAD", e.zrodlo, f"etykieta '{e.tekst}': wypelnij dokladnie jedno z "
                    "Wezel / Odcinek", e.wiazka)
        elif e.wezel and e.wezel not in d.wezly:
            d.dodaj("BLAD", e.zrodlo, f"etykieta '{e.tekst}': nieznany wezel '{e.wezel}'",
                    e.wiazka)
        elif e.odcinek and e.odcinek not in d.odcinki:
            d.dodaj("BLAD", e.zrodlo, f"etykieta '{e.tekst}': nieznany odcinek "
                    f"'{e.odcinek}'", e.wiazka)
    for u in d.uwagi:
        if u.wiazka not in d.wiazki:
            d.dodaj("BLAD", u.zrodlo, f"uwaga {u.nr}: nieznana wiazka '{u.wiazka}'")
        for n in u.wezly:
            if n not in d.wezly:
                d.dodaj("BLAD", u.zrodlo, f"uwaga {u.nr}: nieznany wezel '{n}'", u.wiazka)
    for n in d.uklad:
        if n not in d.wezly:
            d.dodaj("OSTRZEZENIE", "uklad.csv", f"nieznany wezel '{n}' - pominiety")
