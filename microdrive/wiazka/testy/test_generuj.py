# -*- coding: utf-8 -*-
import ezdxf
import fitz

from wiazka.__main__ import main
from wiazka.generuj import generuj


def test_demo_generuje_komplet(demo_dir, tmp_path):
    wyj = tmp_path / "wyj"
    d, gotowe = generuj(demo_dir, wyj)
    assert gotowe == ["DEMO-1"]
    for ext in (".dxf", ".pdf", ".png"):
        assert (wyj / f"DEMO-1{ext}").stat().st_size > 1000, ext
    assert (wyj / "RAPORT_wiazka.txt").exists()
    for n in ("polaczenia", "lista_ciecia", "bom", "piny", "etykiety"):
        assert (wyj / "DEMO-1_tabele" / f"{n}.csv").exists()
    assert fitz.open(wyj / "DEMO-1.pdf").page_count == 5
    doc = ezdxf.readfile(wyj / "DEMO-1.dxf")
    warstwy = {e.dxf.layer for e in doc.modelspace()}
    assert {"WH_WIAZKA", "WH_ZLACZE", "WH_TABELA", "WH_OPIS", "WH_RAMKA"} <= warstwy


def test_blad_nie_rysuje_i_kod_wyjscia(demo_dir, tmp_path, dopisz):
    dopisz(demo_dir, "odcinki.csv", "O-99;DEMO-1;C2;P1;500;;")
    wyj = tmp_path / "wyj"
    assert main([str(demo_dir), "-o", str(wyj)]) == 1
    assert not (wyj / "DEMO-1.dxf").exists()
    raport = (wyj / "RAPORT_wiazka.txt").read_text(encoding="utf-8")
    assert "zamyka petle" in raport


def test_cli_demo(demo_dir, tmp_path):
    assert main([str(demo_dir), "-o", str(tmp_path / "w")]) == 0
