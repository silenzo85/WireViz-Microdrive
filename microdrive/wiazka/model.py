# -*- coding: utf-8 -*-
"""
model.py - model danych wiazki (format: docs/54 projektu Mercedes Microdrive).

Pojecia jak w KBL (VDA 4964): wiazka, wezel, odcinek, zlacze, zyla, oslona.
Wartosc nieznana = None; to, skad sie wziela (TODO/TBD), zapisuje Problem typu BRAK.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

TYPY_WEZLOW = ("ZLACZE", "ROZGALEZIENIE", "SPLICE", "PRZEPUST", "ELEMENT", "UKLAD")
WEZLY_Z_CZESCIA = ("SPLICE", "PRZEPUST", "ELEMENT")  # maja numer katalogowy w BOM
KONCE_ZYL = ("ZLACZE", "SPLICE", "ELEMENT")  # na czym moze konczyc sie zyla
BRAKI = ("TODO", "TBD")


@dataclass
class Problem:
    poziom: str  # BLAD / OSTRZEZENIE / BRAK
    zrodlo: str  # "plik.csv:wiersz" albo nazwa pliku
    tekst: str
    wiazka: Optional[str] = None


@dataclass
class Wiazka:
    id: str
    nazwa: str
    numer: str = ""
    rewizja: str = ""
    miejsce: str = ""
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Wezel:
    id: str
    wiazka: str
    typ: str
    opis: str = ""
    producent: str = ""
    pn: str = ""
    zrodlo: str = ""


@dataclass
class Odcinek:
    id: str
    wiazka: str
    a: str
    b: str
    dlugosc: Optional[int]  # None = TBD
    oslony: List[str] = field(default_factory=list)
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Zlacze:
    oznaczenie: str
    urzadzenie: str
    producent: str
    obudowa: str
    liczba_gniazd: Optional[int]  # None = TODO
    styk: str = ""
    uszczelka: str = ""
    zaslepka: str = ""
    backshell: str = ""
    naddatek: Optional[int] = None
    widok: str = ""
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Zyla:
    id: str
    od: str
    od_gn: str
    do: str
    do_gn: str
    przekroj: str
    kolor: str
    sygnal: str = ""
    typ: str = ""
    kabel: str = ""
    zyla_kabla: str = ""
    skret: str = ""
    naddatek: int = 0
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Oslona:
    id: str
    typ: str
    producent: str = ""
    pn: str = ""
    srednica: str = ""
    kolor: str = ""
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Kabel:
    id: str
    producent: str = ""
    pn: str = ""
    liczba_zyl: str = ""
    ekran: str = ""
    uwagi: str = ""
    zrodlo: str = ""


@dataclass
class Etykieta:
    wiazka: str
    tekst: str
    wezel: str = ""
    odcinek: str = ""
    zrodlo: str = ""


@dataclass
class Uwaga:
    wiazka: str
    nr: str
    tekst: str
    wezly: List[str] = field(default_factory=list)
    zrodlo: str = ""


@dataclass
class Rewizja:
    wiazka: str
    rewizja: str
    data: str = ""
    autor: str = ""
    opis: str = ""


@dataclass
class Dane:
    parametry: Dict[str, str] = field(default_factory=dict)
    naddatek_domyslny: int = 0
    wiazki: Dict[str, Wiazka] = field(default_factory=dict)
    wezly: Dict[str, Wezel] = field(default_factory=dict)
    odcinki: Dict[str, Odcinek] = field(default_factory=dict)
    zlacza: Dict[str, Zlacze] = field(default_factory=dict)
    zyly: Dict[str, Zyla] = field(default_factory=dict)
    oslony: Dict[str, Oslona] = field(default_factory=dict)
    kable: Dict[str, Kabel] = field(default_factory=dict)
    etykiety: List[Etykieta] = field(default_factory=list)
    uwagi: List[Uwaga] = field(default_factory=list)
    rewizje: List[Rewizja] = field(default_factory=list)
    uklad: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    problemy: List[Problem] = field(default_factory=list)

    def dodaj(self, poziom, zrodlo, tekst, wiazka=None):
        self.problemy.append(Problem(poziom, zrodlo, tekst, wiazka))

    def wezly_wiazki(self, wid):
        return [w for w in self.wezly.values() if w.wiazka == wid]

    def odcinki_wiazki(self, wid):
        return [o for o in self.odcinki.values() if o.wiazka == wid]

    def zyly_wiazki(self, wid):
        return [z for z in self.zyly.values()
                if z.od in self.wezly and self.wezly[z.od].wiazka == wid]

    def bledne_wiazki(self) -> Set[str]:
        """Wiazki, ktorych nie wolno rysowac. Blad bez przypisanej wiazki blokuje wszystkie."""
        bledy = [p for p in self.problemy if p.poziom == "BLAD"]
        if any(p.wiazka is None for p in bledy):
            return set(self.wiazki)
        return {p.wiazka for p in bledy}
