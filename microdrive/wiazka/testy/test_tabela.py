# -*- coding: utf-8 -*-
from wiazka.blok_zlacza import BlokZlacza
from wiazka.dane import wczytaj
from wiazka.scena import Scena, Tekst, dopasuj, szer_tekstu
from wiazka.tabela import WIERSZ, Tabela


def test_dopasuj():
    assert dopasuj("krotki", 100, 2.5) == "krotki"
    t = dopasuj("x" * 100, 20, 2.5)
    assert t.endswith("...") and szer_tekstu(t, 2.5) <= 20


def test_tabela_rozmiar_i_teksty_w_obrysie():
    t = Tabela("TYTUL", ["A", "Kolor"], [["1", "BN/WH"], ["22", "RD"]], kolory={1})
    assert t.h == WIERSZ * 4
    sc = Scena(200, 100)
    t.rysuj(sc, 10, 90)
    for e in sc.el:
        if isinstance(e, Tekst):
            szer = szer_tekstu(e.tekst, e.h)
            assert 10 <= e.x and e.x + szer <= 10 + t.w + 0.01, e.tekst


def test_blok_zlacza_c1(demo_dir):
    d = wczytaj(demo_dir)
    b = BlokZlacza(d, "C1")
    assert [r[0] for r in b.wiersze][:3] == ["1", "2", "3"]   # kolejnosc naturalna
    assert len(b.wiersze) == 10
    assert len(b.gn) == 13 and len(b.uzyte) == 10
    wiersz_w11 = [r for r in b.wiersze if r[2] == "W11"][0]
    assert wiersz_w11[1] == "D1.A"
    assert b.w > b.tab.w and b.h >= b.tab.h
