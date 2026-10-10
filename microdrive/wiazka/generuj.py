# -*- coding: utf-8 -*-
"""generuj.py - przebieg: dane -> walidacja -> obliczenia -> rysunek -> pliki."""

from pathlib import Path

import yaml

from .bom import bom
from .dane import wczytaj
from .raport import raport
from .rysuj import arkusz1, dane_tabel, strony
from .topologia import Drzewo, dlugosc_ciecia, zawartosc
from .uklad import uloz
from .walidacja import waliduj
from .wyjscie import zapisz, zapisz_csv

SZABLON = Path(__file__).resolve().parents[1] / "_szablon.yml"


def metadane(d):
    meta = {}
    if SZABLON.exists():
        m = (yaml.safe_load(SZABLON.read_text(encoding="utf-8")) or {}).get("metadata", {})
        meta = {"firma": m.get("company", ""), "projekt": m.get("project", "")}
    for k in ("firma", "projekt", "rysowal", "sprawdzil"):
        if d.parametry.get(k):
            meta[k] = d.parametry[k]
    return meta


def generuj(katalog_danych, katalog_wyj, tylko=None):
    d = wczytaj(katalog_danych)
    waliduj(d)
    wyj = Path(katalog_wyj)
    wyj.mkdir(parents=True, exist_ok=True)
    meta = metadane(d)
    zle = d.bledne_wiazki()
    gotowe = []
    for wid in d.wiazki:
        if (tylko and wid != tylko) or wid in zle:
            continue
        dr = Drzewo(d, wid)
        zaw = zawartosc(d, dr)
        dl = {z.id: dlugosc_ciecia(d, dr, z) for z in d.zyly_wiazki(wid)}
        poz = bom(d, dr, dl)
        ul = uloz(d, dr, zaw)
        tab = dane_tabel(d, wid, poz, dl)
        st = strony(d, wid, tab, meta)
        sc = arkusz1(d, wid, ul, zaw, poz, meta, 1 + len(st))
        zapisz([sc] + st, wyj / wid)
        zapisz_csv(wyj / f"{wid}_tabele", tab)
        gotowe.append(wid)
    raport(d, wyj / "RAPORT_wiazka.txt", gotowe)
    return d, gotowe
