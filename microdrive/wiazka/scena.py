# -*- coding: utf-8 -*-
"""
scena.py - rysunek jako lista prymitywow w mm (y w gore, jak w DXF).

Jedna scena -> DXF -> PDF/PNG: PDF i DXF nie moga sie rozjechac.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

# Arial: zmierzona szerokosc znaku 0,64-0,70 wysokosci (tekst mieszany),
# 0,76 (same cyfry). Jak w wv_dxf.CHAR_W: 0,72 z zapasem.
SZER_ZNAKU = 0.72


def szer_tekstu(t, h):
    return len(str(t)) * h * SZER_ZNAKU


def dopasuj(t, max_w, h):
    """Docina tekst do szerokosci, dokladajac wielokropek."""
    t = str(t).replace("\n", " ")
    n = max(int(max_w / (h * SZER_ZNAKU)), 1)
    return t if len(t) <= n else t[:max(n - 3, 1)] + "..."


@dataclass
class Linia:
    pts: List[Tuple[float, float]]
    warstwa: str
    rgb: Optional[Tuple[int, int, int]] = None


@dataclass
class Wielokat:
    pts: List[Tuple[float, float]]
    rgb: Tuple[int, int, int]
    warstwa: str


@dataclass
class Tekst:
    tekst: str
    x: float
    y: float  # srodek wysokosci tekstu
    h: float
    warstwa: str
    wyr: str = "L"  # L / C / R
    rgb: Optional[Tuple[int, int, int]] = None


@dataclass
class Okrag:
    x: float
    y: float
    r: float
    warstwa: str
    rgb: Optional[Tuple[int, int, int]] = None
    wypelniony: bool = False


class Scena:
    def __init__(self, w, h):
        self.w, self.h, self.el = w, h, []

    def linia(self, pts, warstwa, rgb=None):
        self.el.append(Linia([tuple(p) for p in pts], warstwa, rgb))

    def prost(self, x, y, w, h, warstwa, rgb=None):
        self.linia([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], warstwa, rgb)

    def wielokat(self, pts, rgb, warstwa):
        self.el.append(Wielokat([tuple(p) for p in pts], rgb, warstwa))

    def wyp(self, x, y, w, h, rgb, warstwa):
        self.wielokat([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], rgb, warstwa)

    def tekst(self, t, x, y, h, warstwa, wyr="L", rgb=None):
        if str(t):
            self.el.append(Tekst(str(t), x, y, h, warstwa, wyr, rgb))

    def okrag(self, x, y, r, warstwa, rgb=None, wypelniony=False):
        self.el.append(Okrag(x, y, r, warstwa, rgb, wypelniony))
