# -*- coding: utf-8 -*-
from wiazka.dane import wczytaj
from wiazka.topologia import Drzewo, dlugosc_ciecia, zawartosc


def przygotuj(katalog):
    d = wczytaj(katalog)
    return d, Drzewo(d, "DEMO-1")


def test_droga(demo_dir):
    d, dr = przygotuj(demo_dir)
    assert dr.droga("C1", "P1") == ["O-1", "O-2", "O-3", "O-4"]
    assert dr.droga("C4", "C1") == ["O-10", "O-9", "O-1"]
    assert dr.droga("C1", "C1") == []


def test_dlugosci_ciecia(demo_dir):
    d, dr = przygotuj(demo_dir)
    # 300+150+1200+2100 + naddatek C1 (domyslny 50) + P1 (wlasny 30)
    assert dlugosc_ciecia(d, dr, d.zyly["W1"]) == 3830
    # 300+100 + 50 (C1) + 50 (D1, element - domyslny)
    assert dlugosc_ciecia(d, dr, d.zyly["W11"]) == 500
    assert dlugosc_ciecia(d, dr, d.zyly["W13"]) == 800
    # droga przez O-7 = TBD
    assert dlugosc_ciecia(d, dr, d.zyly["W8"]) is None


def test_naddatek_zyly(demo_dir, zastap):
    zastap(demo_dir, "przewody.csv", "W1;C1;1;P1;1;0,5;RD;ZASIL+;DEMO-FLRY 0,5;;;W2;;",
           "W1;C1;1;P1;1;0,5;RD;ZASIL+;DEMO-FLRY 0,5;;;W2;100;")
    d, dr = przygotuj(demo_dir)
    assert dlugosc_ciecia(d, dr, d.zyly["W1"]) == 3930


def test_zawartosc(demo_dir):
    d, dr = przygotuj(demo_dir)
    z = zawartosc(d, dr)
    assert len(z["O-1"]) == 10
    assert sorted(z["O-4"]) == ["W1", "W2", "W3", "W4"]
    assert sorted(z["O-9"]) == ["W11", "W13"]
    assert z["O-7"] == ["W8"]
    assert sorted(z["O-8"]) == ["W10", "W9"]
