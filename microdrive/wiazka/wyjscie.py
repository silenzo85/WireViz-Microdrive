# -*- coding: utf-8 -*-
"""
wyjscie.py - scena -> DXF (ezdxf), PDF/PNG renderowane z TEGO SAMEGO DXF, tabele -> CSV.
"""

import csv
from pathlib import Path

import ezdxf
import fitz
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import BoundingBox2d

from .scena import Linia, Okrag, Tekst, Wielokat

WARSTWY = {  # nazwa: kolor ACI
    "WH_RAMKA": 7, "WH_WIAZKA": 7, "WH_WEZEL": 7, "WH_ZLACZE": 5,
    "WH_TABELA": 8, "WH_OPIS": 7, "WH_KOLOR": 7, "WH_UWAGA": 1,
}
WYROWNANIE = {"L": TextEntityAlignment.MIDDLE_LEFT,
              "C": TextEntityAlignment.MIDDLE_CENTER,
              "R": TextEntityAlignment.MIDDLE_RIGHT}
STYL = "ARIAL"


def do_dxf(sc):
    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.MM
    if STYL not in doc.styles:
        doc.styles.add(STYL, font="arial.ttf")
    for nazwa, aci in WARSTWY.items():
        doc.layers.add(nazwa, color=aci)
    msp = doc.modelspace()
    for e in sc.el:
        a = {"layer": e.warstwa}
        if isinstance(e, Linia):
            p = msp.add_lwpolyline(e.pts, dxfattribs=a)
            if e.rgb:
                p.rgb = e.rgb
        elif isinstance(e, Wielokat):
            h = msp.add_hatch(color=7, dxfattribs=a)
            h.paths.add_polyline_path(e.pts, is_closed=True)
            h.rgb = e.rgb
        elif isinstance(e, Tekst):
            t = msp.add_text(e.tekst, height=e.h, dxfattribs={**a, "style": STYL})
            t.set_placement((e.x, e.y), align=WYROWNANIE[e.wyr])
            if e.rgb:
                t.rgb = e.rgb
        elif isinstance(e, Okrag):
            if e.wypelniony:
                h = msp.add_hatch(color=7, dxfattribs=a)
                h.paths.add_edge_path().add_arc((e.x, e.y), e.r, 0, 360)
                h.rgb = e.rgb or (0, 0, 0)
            else:
                c = msp.add_circle((e.x, e.y), e.r, dxfattribs=a)
                if e.rgb:
                    c.rgb = e.rgb
    return doc


def renderuj(doc, w, h, fmt="pdf", dpi=110):
    be = PyMuPdfBackend()
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.COLOR)
    Frontend(RenderContext(doc), be, config=cfg).draw_layout(doc.modelspace())
    strona = layout.Page(w, h, layout.Units.mm, margins=layout.Margins.all(0))
    pole = BoundingBox2d([(0, 0), (w, h)])
    if fmt == "pdf":
        return be.get_pdf_bytes(strona, render_box=pole)
    return be.get_pixmap_bytes(strona, fmt="png", dpi=dpi, render_box=pole)


def zapisz(sceny, baza):
    """baza = sciezka bez rozszerzenia. DXF i PNG = arkusz 1, PDF = wszystkie strony."""
    baza = str(baza)
    docs = [do_dxf(s) for s in sceny]
    docs[0].saveas(baza + ".dxf")
    pdf = fitz.open()
    for doc, s in zip(docs, sceny):
        pdf.insert_pdf(fitz.open("pdf", renderuj(doc, s.w, s.h, "pdf")))
    pdf.save(baza + ".pdf")
    Path(baza + ".png").write_bytes(renderuj(docs[0], sceny[0].w, sceny[0].h, "png"))


def zapisz_csv(katalog, tabele):
    k = Path(katalog)
    k.mkdir(parents=True, exist_ok=True)
    for nazwa, (nagl, wiersze, _) in tabele.items():
        with open(k / f"{nazwa}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(nagl)
            w.writerows(wiersze)
