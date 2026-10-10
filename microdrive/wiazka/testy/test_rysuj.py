# -*- coding: utf-8 -*-
from wiazka.bom import bom
from wiazka.dane import wczytaj
from wiazka.rysuj import arkusz1, dane_tabel, strony
from wiazka.scena import Tekst, szer_tekstu
from wiazka.topologia import Drzewo, dlugosc_ciecia, zawartosc
from wiazka.uklad import uloz

META = {"firma": "DEMARKO", "projekt": "TEST", "rysowal": "test"}


def zbuduj(katalog):
    d = wczytaj(katalog)
    dr = Drzewo(d, "DEMO-1")
    zaw = zawartosc(d, dr)
    dl = {z.id: dlugosc_ciecia(d, dr, z) for z in d.zyly_wiazki("DEMO-1")}
    poz = bom(d, dr, dl)
    ul = uloz(d, dr, zaw)
    tab = dane_tabel(d, "DEMO-1", poz, dl)
    st = strony(d, "DEMO-1", tab, META)
    sc = arkusz1(d, "DEMO-1", ul, zaw, poz, META, 1 + len(st))
    return d, tab, st, sc


def teksty_w_arkuszu(sc):
    for e in sc.el:
        if isinstance(e, Tekst):
            w = szer_tekstu(e.tekst, e.h)
            x0 = {"L": e.x, "C": e.x - w / 2, "R": e.x - w}[e.wyr]
            assert 0 <= x0 and x0 + w <= sc.w, e.tekst
            assert 0 <= e.y - e.h / 2 and e.y + e.h / 2 <= sc.h, e.tekst


def test_dane_tabel(demo_dir):
    d, tab, st, sc = zbuduj(demo_dir)
    assert set(tab) == {"polaczenia", "lista_ciecia", "bom", "piny", "etykiety"}
    nagl, wiersze, _ = tab["polaczenia"]
    w1 = [w for w in wiersze if w[2] == "W1"][0]
    assert w1[0] == "C1.1" and w1[1] == "P1.1" and w1[8] == "3830"
    w8 = [w for w in wiersze if w[2] == "W8"][0]
    assert w8[1] == "S1" and w8[8] == "TBD"


def test_arkusz1_tekst_w_arkuszu_i_tbd(demo_dir):
    d, tab, st, sc = zbuduj(demo_dir)
    teksty_w_arkuszu(sc)
    t = [e.tekst for e in sc.el if isinstance(e, Tekst)]
    assert any("NIEPOTWIERDZONE" in x for x in t)
    assert any(x.startswith("TBD") for x in t)          # opis odcinka O-7
    assert "LISTA MATERIALOW" in t and "UWAGI" in t and "REWIZJE" in t


def test_strony(demo_dir):
    d, tab, st, sc = zbuduj(demo_dir)
    assert len(st) == 4          # polaczenia, lista ciecia, BOM, etykiety (malo wierszy)
    for s in st:
        teksty_w_arkuszu(s)
