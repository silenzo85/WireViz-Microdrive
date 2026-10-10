# -*- coding: utf-8 -*-
from wiazka.dane import wczytaj


def poziomy(d, poziom):
    return [p for p in d.problemy if p.poziom == poziom]


def test_demo_wczytuje_sie_bez_bledow(demo_dir):
    d = wczytaj(demo_dir)
    assert poziomy(d, "BLAD") == []
    assert set(d.wiazki) == {"DEMO-1"}
    assert len(d.wezly) == 11 and len(d.odcinki) == 10
    assert len(d.zlacza) == 5 and len(d.zyly) == 13
    assert d.naddatek_domyslny == 50
    assert d.odcinki["O-3"].oslony == ["OP1", "TK1"]
    assert d.zlacza["P1"].naddatek == 30
    assert d.zlacza["C1"].liczba_gniazd == 13


def test_tbd_i_todo_sa_brakami(demo_dir):
    d = wczytaj(demo_dir)
    assert d.odcinki["O-7"].dlugosc is None
    braki = " | ".join(p.zrodlo + " " + p.tekst for p in poziomy(d, "BRAK"))
    assert "odcinki.csv" in braki and "Dlugosc mm = TBD" in braki
    assert "Obudowa = TODO" in braki


def test_brak_pliku_wymaganego(demo_dir):
    (demo_dir / "przewody.csv").unlink()
    d = wczytaj(demo_dir)
    assert any(p.zrodlo == "przewody.csv" and "brak wymaganego pliku" in p.tekst
               for p in poziomy(d, "BLAD"))
    assert d.bledne_wiazki() == {"DEMO-1"}


def test_pusta_kolumna_wymagana(demo_dir, dopisz):
    dopisz(demo_dir, "odcinki.csv", "O-99;DEMO-1;C1;;100;;")
    d = wczytaj(demo_dir)
    assert any("pusta kolumna wymagana: Wezel B" in p.tekst for p in poziomy(d, "BLAD"))
    assert "O-99" not in d.odcinki


def test_zla_liczba(demo_dir, zastap):
    zastap(demo_dir, "odcinki.csv", "O-1;DEMO-1;C1;B1;300", "O-1;DEMO-1;C1;B1;3OO")
    d = wczytaj(demo_dir)
    assert any("Dlugosc mm: '3OO' nie jest liczba" in p.tekst for p in poziomy(d, "BLAD"))


def test_duplikat_id(demo_dir, dopisz):
    dopisz(demo_dir, "przewody.csv", "W1;C1;8;P1;1;0,5;RD;;;;;;;")
    d = wczytaj(demo_dir)
    assert any("powtorzony ID zyly 'W1'" in p.tekst for p in poziomy(d, "BLAD"))


def test_brak_kolumny(demo_dir, zastap):
    zastap(demo_dir, "wezly.csv", "Numer katalogowy", "Nr kat")
    d = wczytaj(demo_dir)
    assert any(p.zrodlo == "wezly.csv" and "Numer katalogowy" in p.tekst
               for p in poziomy(d, "BLAD"))
