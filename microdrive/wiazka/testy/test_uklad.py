# -*- coding: utf-8 -*-
from wiazka.blok_zlacza import BlokZlacza
from wiazka.dane import wczytaj
from wiazka.topologia import Drzewo, zawartosc
from wiazka.uklad import uloz


def przygotuj(katalog):
    d = wczytaj(katalog)
    dr = Drzewo(d, "DEMO-1")
    return d, uloz(d, dr, zawartosc(d, dr))


def prostokaty(d, ul):
    wyn = []
    for zid, (x, y, s) in ul.bloki.items():
        b = BlokZlacza(d, zid)
        wyn.append((zid, x, y, x + b.w, y + b.h))
    return wyn


def test_wszystko_rozmieszczone(demo_dir):
    d, ul = przygotuj(demo_dir)
    assert set(ul.poz) == set(d.wezly)
    assert set(ul.trasy) == set(d.odcinki)
    assert set(ul.bloki) == set(d.zlacza)
    assert ul.korzen == "C1"
    assert ul.poz["C1"] == (0.0, 0.0)


def test_bloki_sie_nie_nakladaja(demo_dir):
    d, ul = przygotuj(demo_dir)
    r = prostokaty(d, ul)
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            a, b = r[i], r[j]
            rozlaczne = a[3] <= b[1] or b[3] <= a[1] or a[4] <= b[2] or b[4] <= a[2]
            assert rozlaczne, f"nakladaja sie bloki {a[0]} i {b[0]}"


def test_trasy_zaczynaja_i_koncza_w_wezlach(demo_dir):
    d, ul = przygotuj(demo_dir)

    def zaokr(p):
        return round(p[0], 6), round(p[1], 6)

    for oid, trasa in ul.trasy.items():
        o = d.odcinki[oid]
        assert {zaokr(trasa[0]), zaokr(trasa[-1])} == {zaokr(ul.poz[o.a]),
                                                      zaokr(ul.poz[o.b])}, oid


def test_bbox_obejmuje_bloki(demo_dir):
    d, ul = przygotuj(demo_dir)
    x0, y0, x1, y1 = ul.bbox
    for zid, a, b, c, e in prostokaty(d, ul):
        assert x0 <= a and c <= x1 and y0 <= b and e <= y1, zid


def test_uklad_csv_nadpisuje(demo_dir):
    (demo_dir / "uklad.csv").write_text("Wezel;X mm;Y mm\nB3;500;-300\n", encoding="utf-8")
    d, ul = przygotuj(demo_dir)
    assert ul.poz["B3"] == (500.0, -300.0)
    assert (500.0, -300.0) in (ul.trasy["O-5"][0], ul.trasy["O-5"][-1])
