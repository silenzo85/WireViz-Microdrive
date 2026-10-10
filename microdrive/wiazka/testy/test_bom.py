# -*- coding: utf-8 -*-
from wiazka.bom import bom
from wiazka.dane import wczytaj
from wiazka.topologia import Drzewo, dlugosc_ciecia


def lista(katalog):
    d = wczytaj(katalog)
    dr = Drzewo(d, "DEMO-1")
    dl = {z.id: dlugosc_ciecia(d, dr, z) for z in d.zyly_wiazki("DEMO-1")}
    return {(p.typ, p.pn): p.ilosc for p in bom(d, dr, dl)}


def test_bom_demo(demo_dir):
    b = lista(demo_dir)
    assert b[("Zlacze", "DEMO-13P")] == "1"
    assert b[("Zlacze", "TODO")] == "1"
    assert b[("Styk", "DEMO-STYK-20")] == "14"      # C1: 10 zajetych + P1: 4
    assert b[("Uszczelka", "DEMO-USZCZ-20")] == "10"
    assert b[("Zaslepka", "DEMO-ZASL")] == "3"        # C1: 13 - 10
    assert b[("Backshell", "DEMO-BS-13")] == "1"
    assert b[("Splice", "DEMO-SPL-1")] == "1"
    assert b[("Przepust", "DEMO-GROM-58")] == "1"
    assert b[("Element", "DEMO-1N4001")] == "1"
    assert b[("Oslona", "DEMO-OPLOT-10")] == "5850 mm"
    assert b[("Oslona", "DEMO-TK-12")] == "1500 mm"
    assert b[("Kabel", "DEMO-3x0,35-EKR")] == "3850 mm"
    assert b[("Etykieta", "")] == "2"


def test_przewody_grupowane_i_tbd(demo_dir):
    b = lista(demo_dir)
    przewody = {k: v for k, v in b.items() if k[0] == "Przewod"}
    # W8 (BU 0,75) idzie przez odcinek TBD -> ilosc nieznana (BU sortuje sie ostatnia)
    assert "TBD" in przewody[("Przewod", "DEMO-FLRY 0,75")]
    assert all(k[1] != "" for k in przewody)
