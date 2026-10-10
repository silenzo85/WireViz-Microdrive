# -*- coding: utf-8 -*-
"""
scena.py - rysunek jako lista prymitywow w mm (y w gore, jak w DXF).

Jedna scena -> DXF -> PDF/PNG: PDF i DXF nie moga sie rozjechac.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

# Szerokosc tekstu MIERZONA czcionka Arial (ta sama, ktora renderuje PDF/PNG).
# Staly wspolczynnik (0,72 z wv_dxf) nie wystarcza: WIELKIE litery i cyfry w Arialu
# to ~0,86 wysokosci - tabele z numerami katalogowymi wychodzily poza kolumny.
# Gdy czcionki brak, zapasowo 0,9 wysokosci na znak (raczej za szeroko niz za wasko).
SZER_ZNAKU = 0.9
ZAPAS = 1.04  # margines na roznice renderera

try:
    from ezdxf.fonts import fonts as _fonts
    _arial = _fonts.make_font("arial.ttf", 1.0)
except Exception:  # pragma: no cover - brak czcionki w systemie
    _arial = None


def szer_tekstu(t, h):
    t = str(t)
    if _arial is not None:
        return _arial.text_width(t) * h * ZAPAS
    return len(t) * h * SZER_ZNAKU


def dopasuj(t, max_w, h):
    """Docina tekst do szerokosci, dokladajac wielokropek."""
    t = str(t).replace("\n", " ")
    if szer_tekstu(t, h) <= max_w + 1e-6:
        return t
    for n in range(len(t) - 1, 0, -1):
        k = t[:n] + "..."
        if szer_tekstu(k, h) <= max_w + 1e-6:
            return k
    return t[:1]


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
