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
    sprawdz_bloki(d, ul)


def sprawdz_bloki(d, ul):
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
        rodzic, dziecko = ul.krawedz[oid]
        # koniec = wezel dziecka; poczatek = wezel rodzica albo punkt na jego belce
        assert zaokr(trasa[-1]) == zaokr(ul.poz[dziecko]), oid
        px, py = ul.poz[rodzic]
        sx, sy = trasa[0]
        if (round(sx, 6), round(sy, 6)) != zaokr((px, py)):
            bx, y0, y1 = ul.belki[rodzic]
            assert abs(sx - bx) < 1e-6 and y0 - 1e-6 <= sy <= y1 + 1e-6, oid


def test_bbox_obejmuje_bloki(demo_dir):
    d, ul = przygotuj(demo_dir)
    x0, y0, x1, y1 = ul.bbox
    for zid, a, b, c, e in prostokaty(d, ul):
        assert x0 <= a and c <= x1 and y0 <= b and e <= y1, zid


def _segmenty(trasa):
    return [(trasa[i], trasa[i + 1]) for i in range(len(trasa) - 1)
            if trasa[i] != trasa[i + 1]]


def _kolizja(s, t, dozwolone, eps=1e-6):
    """Przeciecie albo wspolliniowe nakladanie dwoch odcinkow poza punktami z 'dozwolone'."""
    (ax, ay), (bx, by) = s
    (cx, cy), (dx, dy) = t

    def orient(px, py, qx, qy, rx, ry):
        v = (qx - px) * (ry - py) - (qy - py) * (rx - px)
        return 0 if abs(v) < eps else (1 if v > 0 else -1)

    o1, o2 = orient(ax, ay, bx, by, cx, cy), orient(ax, ay, bx, by, dx, dy)
    o3, o4 = orient(cx, cy, dx, dy, ax, ay), orient(cx, cy, dx, dy, bx, by)
    if o1 == o2 == o3 == o4 == 0:          # wspolliniowe - nakladaja sie na dlugosci?
        if abs(bx - ax) > abs(by - ay):
            lo, hi = sorted((ax, bx)), sorted((cx, dx))
        else:
            lo, hi = sorted((ay, by)), sorted((cy, dy))
        return min(lo[1], hi[1]) - max(lo[0], hi[0]) > 0.5
    if o1 != o2 and o3 != o4:
        # punkt przeciecia
        den = (ax - bx) * (cy - dy) - (ay - by) * (cx - dx)
        tt = ((ax - cx) * (cy - dy) - (ay - cy) * (cx - dx)) / den
        p = (ax + tt * (bx - ax), ay + tt * (by - ay))
        return not any(abs(p[0] - q[0]) < 0.01 and abs(p[1] - q[1]) < 0.01 for q in dozwolone)
    return False


def _odl_pkt_odc(p, s):
    (ax, ay), (bx, by) = s
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / L))
    return ((p[0] - ax - t * vx) ** 2 + (p[1] - ay - t * vy) ** 2) ** 0.5


PRZESWIT = 4.0     # rurka ma 3,2 mm szerokosci; ponizej tego trasy zlewaja sie w jeden pas
OKOLICA = 15.0     # przy samym wezle galezie z definicji sie schodza


def sprawdz_trasy(d, ul):
    """Zadne dwie trasy nie przecinaja sie ani nie biegna blizej niz PRZESWIT (poza wezlem)."""
    wezly = list(ul.poz.values())
    trasy = list(ul.trasy.items())
    for i in range(len(trasy)):
        for j in range(i + 1, len(trasy)):
            for s in _segmenty(trasy[i][1]):
                for t in _segmenty(trasy[j][1]):
                    assert not _kolizja(s, t, wezly), f"{trasy[i][0]} koliduje z {trasy[j][0]}"
                    (ax, ay), (bx, by) = s
                    n = max(int(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5), 1)
                    for k in range(n + 1):
                        p = (ax + (bx - ax) * k / n, ay + (by - ay) * k / n)
                        if any(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 < OKOLICA
                               for q in wezly):
                            continue
                        dist = _odl_pkt_odc(p, t)
                        assert dist >= PRZESWIT, (f"{trasy[i][0]} i {trasy[j][0]} za blisko: "
                                                  f"{dist:.1f} mm w punkcie {p}")


def test_trasy_sie_nie_nakladaja_demo(demo_dir):
    d, ul = przygotuj(demo_dir)
    sprawdz_trasy(d, ul)


def test_trasy_sie_nie_nakladaja_wezel_z_wieloma_galeziami(demo_dir, dopisz):
    # Wada zgloszona przez usera: przy wezle z wieloma galeziami (B-TTC: 9 kabli)
    # galezie szly prawie pionowo, rownolegle, i zlewaly sie w jeden pas.
    for i in range(1, 9):
        dopisz(demo_dir, "wezly.csv", f"X{i};DEMO-1;ZLACZE;;;")
        dopisz(demo_dir, "zlacza.csv", f"X{i};URZ{i};DEMO;DEMO-2P;2;;;;;;;")
        dopisz(demo_dir, "odcinki.csv", f"O-X{i};DEMO-1;B1;X{i};{1000 * i};;")
        dopisz(demo_dir, "przewody.csv", f"WX{i};C1;13;X{i};1;0,5;RD;;;;;;;"
               if i == 1 else f"WX{i};X{i};1;X{i - 1};2;0,5;RD;;;;;;;")
    d, ul = przygotuj(demo_dir)
    sprawdz_trasy(d, ul)


def test_trasy_sie_nie_nakladaja_dane_projektu():
    import pytest
    from pathlib import Path
    dane = Path(__file__).resolve().parents[4] / "docs" / "45_wireviz" / "wiazki"
    if not (dane / "wiazki.csv").exists():
        pytest.skip("brak tabel wiazek projektu")
    d = wczytaj(dane)
    for wid in d.wiazki:
        dr = Drzewo(d, wid)
        ul = uloz(d, dr, zawartosc(d, dr))
        sprawdz_bloki(d, ul)   # zlacza "w linii" (para zlaczy na ogonku) nachodzily na siebie
        sprawdz_trasy(d, ul)


def test_uklad_csv_nadpisuje(demo_dir):
    (demo_dir / "uklad.csv").write_text("Wezel;X mm;Y mm\nB3;500;-300\n", encoding="utf-8")
    d, ul = przygotuj(demo_dir)
    assert ul.poz["B3"] == (500.0, -300.0)
    assert (500.0, -300.0) in (ul.trasy["O-5"][0], ul.trasy["O-5"][-1])
