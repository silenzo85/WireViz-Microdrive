# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from wiazka.dane import wczytaj
from wiazka.szablon import _kolor_csv, _liczba_gniazd, main, zapisz, zbuduj
from wiazka.walidacja import waliduj

DANE = Path(__file__).resolve().parents[4] / "docs" / "45_wireviz"
jest_dane = pytest.mark.skipif(not (DANE / "02_urzadzenia_piny.csv").exists(),
                               reason="brak danych projektu docs/45_wireviz")


def test_liczba_gniazd_tylko_jednoznaczna():
    assert _liczba_gniazd("Deutsch DT04-2P") == 2
    assert _liczba_gniazd("C1: TE Superseal 1.0, 34-pin") == 34
    assert _liczba_gniazd("MPM 3-biegunowe") == 3
    assert _liczba_gniazd("P1 M12 4-pin B-coded, P2 M12 12-pin A-coded", "P2") == 12
    assert _liczba_gniazd("P1 M12 4-pin, P2 M12 12-pin") is None    # dwie liczby - nie zgadujemy
    assert _liczba_gniazd("TODO_HARDWARE") is None


def test_kolor_csv():
    assert _kolor_csv("BNWH") == "BN/WH"
    assert _kolor_csv("RD") == "RD"


@jest_dane
def test_szablon_z_danych_projektu_przechodzi_walidacje(tmp_path):
    tabele, raport = zbuduj(DANE)
    zapisz(tabele, raport, tmp_path, "test")
    d = wczytaj(tmp_path)
    waliduj(d)
    bledy = [p.tekst for p in d.problemy if p.poziom == "BLAD"]
    assert bledy == []
    # gniazdo TTC = jedna zyla: wspolne piny zasilania ida przez splice
    assert "SPL-P149" in d.wezly and d.wezly["SPL-P149"].typ == "SPLICE"
    do_ttc = [(z.do, z.do_gn) for z in d.zyly.values() if z.do.startswith("TTC-")]
    assert len(do_ttc) == len(set(do_ttc))


@jest_dane
def test_nie_nadpisuje_wypelnionych_tabel(tmp_path):
    (tmp_path / "zlacza.csv").write_text("cos recznie wpisanego\n", encoding="utf-8")
    assert main(["--wyjscie", str(tmp_path)]) == 2
    assert (tmp_path / "zlacza.csv").read_text(encoding="utf-8") == "cos recznie wpisanego\n"
