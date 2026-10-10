# -*- coding: utf-8 -*-
from wiazka.dane import wczytaj
from wiazka.kolor import kody_koloru, rgb
from wiazka.walidacja import waliduj


def sprawdz(katalog):
    d = wczytaj(katalog)
    waliduj(d)
    return d


def bledy(d):
    return [p.tekst for p in d.problemy if p.poziom == "BLAD"]


def test_kolory():
    assert kody_koloru("BN/WH") == ["BN", "WH"]
    assert kody_koloru("ye") == ["YE"]
    assert kody_koloru("XX") is None
    assert kody_koloru("BN/WH/RD") is None
    assert rgb("BU") == (0x00, 0x66, 0xFF)


def test_demo_bez_bledow(demo_dir):
    d = sprawdz(demo_dir)
    assert bledy(d) == []
    assert d.bledne_wiazki() == set()


def test_petla(demo_dir, dopisz):
    dopisz(demo_dir, "odcinki.csv", "O-99;DEMO-1;C2;P1;500;;")
    d = sprawdz(demo_dir)
    assert any("zamyka petle" in t for t in bledy(d))
    assert d.bledne_wiazki() == {"DEMO-1"}


def test_niespojne(demo_dir, dopisz):
    dopisz(demo_dir, "wezly.csv", "B9;DEMO-1;ROZGALEZIENIE;;;")
    d = sprawdz(demo_dir)
    assert any("drzewo niespojne" in t for t in bledy(d))


def test_gniazdo_poza_zakresem(demo_dir, zastap):
    zastap(demo_dir, "przewody.csv", "W1;C1;1;P1;1;", "W1;C1;1;P1;7;")
    assert any("P1.7 poza zakresem 1..4" in t for t in bledy(sprawdz(demo_dir)))


def test_gniazdo_zajete_dwa_razy(demo_dir, dopisz):
    dopisz(demo_dir, "przewody.csv", "W99;C1;1;C2;3;0,5;RD;;;;;;;")
    assert any("C1.1 zajete dwa razy" in t for t in bledy(sprawdz(demo_dir)))


def test_splice_z_gniazdem(demo_dir, zastap):
    zastap(demo_dir, "przewody.csv", "W9;S1;;C3", "W9;S1;1;C3")
    assert any("splice S1 nie ma gniazd" in t for t in bledy(sprawdz(demo_dir)))


def test_zlacze_bez_wiersza(demo_dir, dopisz):
    dopisz(demo_dir, "wezly.csv", "C9;DEMO-1;ZLACZE;;;")
    dopisz(demo_dir, "odcinki.csv", "O-99;DEMO-1;B3;C9;100;;")
    assert any("C9: brak wiersza w zlacza.csv" in t for t in bledy(sprawdz(demo_dir)))


def test_zyla_miedzy_wiazkami(demo_dir, dopisz):
    dopisz(demo_dir, "wiazki.csv", "DEMO-2;Druga;;;;")
    dopisz(demo_dir, "wezly.csv", "X1;DEMO-2;ZLACZE;;;")
    dopisz(demo_dir, "zlacza.csv", "X1;URZ;DEMO;DEMO-1P;1;;;;;;;")
    dopisz(demo_dir, "przewody.csv", "W99;C1;13;X1;1;0,5;RD;;;;;;;")
    assert any("laczy dwie wiazki" in t for t in bledy(sprawdz(demo_dir)))


def test_nieznany_kolor(demo_dir, zastap):
    zastap(demo_dir, "przewody.csv", ";0,5;RD;ZASIL+", ";0,5;CZERWONY;ZASIL+")
    assert any("nieznany kolor 'CZERWONY'" in t for t in bledy(sprawdz(demo_dir)))


def test_element_bez_numeru(demo_dir, zastap):
    zastap(demo_dir, "wezly.csv", "DEMO;DEMO-1N4001", ";")
    assert any("D1 (ELEMENT): wymagany Numer katalogowy" in t for t in bledy(sprawdz(demo_dir)))


def test_osierocone_zlacze_to_ostrzezenie(demo_dir, dopisz):
    dopisz(demo_dir, "wezly.csv", "C9;DEMO-1;ZLACZE;;;")
    dopisz(demo_dir, "zlacza.csv", "C9;URZ;DEMO;DEMO-1P;1;;;;;;;")
    dopisz(demo_dir, "odcinki.csv", "O-99;DEMO-1;B3;C9;100;;")
    d = sprawdz(demo_dir)
    assert bledy(d) == []
    assert any(p.poziom == "OSTRZEZENIE" and "C9" in p.tekst for p in d.problemy)


def test_etykieta_dokladnie_jedno(demo_dir, dopisz):
    dopisz(demo_dir, "etykiety.csv", "DEMO-1;ZLE;C1;O-1;")
    assert any("dokladnie jedno" in t for t in bledy(sprawdz(demo_dir)))
