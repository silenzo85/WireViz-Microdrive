# -*- coding: utf-8 -*-
"""
kolor.py - kody kolorow zyl -> RGB probek.

Kody jak w WireViz (BK, BN, RD, ...), ta sama tabela co w reszcie rysunkow projektu.
Zyla w paski: 'BAZA/PASEK', np. 'BN/WH'.
"""

from wireviz.wv_colors import _color_hex


def kody_koloru(kolor):
    """'BN/WH' -> ['BN', 'WH']; 'YE' -> ['YE']; nieznany albo >2 kolory -> None."""
    czesci = [c.strip().upper() for c in str(kolor).split("/") if c.strip()]
    if not czesci or len(czesci) > 2 or any(c not in _color_hex for c in czesci):
        return None
    return czesci


def rgb(kod):
    h = _color_hex[kod].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
