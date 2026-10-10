# -*- coding: utf-8 -*-
"""
dane.py - wczytanie tabel wiazki (CSV, separator ';', UTF-8) do modelu.

Bledy FORMATU (brak pliku, brak kolumny, pusta kolumna wymagana, zla liczba,
duplikat ID) -> Dane.problemy jako BLAD. Wartosci TODO/TBD -> BRAK.
Bledy ZNACZENIOWE (petle, zle odwolania) sprawdza walidacja.py.
"""

import csv
from pathlib import Path

from .model import (BRAKI, Dane, Etykieta, Kabel, Odcinek, Oslona, Rewizja, Uwaga,
                    Wezel, Wiazka, Zlacze, Zyla)

# plik: (plik wymagany, wszystkie kolumny, kolumny wymagane W)
TABELE = {
    "parametry.csv": (False, ["Parametr", "Wartosc", "Uwagi"], ["Parametr", "Wartosc"]),
    "wiazki.csv": (True, ["ID wiazki", "Nazwa", "Numer rysunku", "Rewizja",
                          "Miejsce montazu", "Uwagi"], ["ID wiazki", "Nazwa"]),
    "wezly.csv": (True, ["ID wezla", "ID wiazki", "Typ", "Opis", "Producent",
                         "Numer katalogowy"], ["ID wezla", "ID wiazki", "Typ"]),
    "odcinki.csv": (True, ["ID odcinka", "ID wiazki", "Wezel A", "Wezel B", "Dlugosc mm",
                           "Oslony", "Uwagi"],
                    ["ID odcinka", "ID wiazki", "Wezel A", "Wezel B", "Dlugosc mm"]),
    "zlacza.csv": (True, ["Oznaczenie", "Urzadzenie", "Producent", "Obudowa", "Liczba gniazd",
                          "Styk", "Uszczelka", "Zaslepka", "Backshell", "Naddatek mm",
                          "Widok czola", "Uwagi"],
                   ["Oznaczenie", "Urzadzenie", "Producent", "Obudowa", "Liczba gniazd"]),
    "przewody.csv": (True, ["ID zyly", "Od zlacze", "Od gniazdo", "Do zlacze", "Do gniazdo",
                            "Przekroj mm2", "Kolor", "Sygnal", "Typ przewodu", "Kabel",
                            "Zyla w kablu", "Skrecona z", "Naddatek mm", "Uwagi"],
                     ["ID zyly", "Od zlacze", "Do zlacze", "Przekroj mm2", "Kolor"]),
    "oslony.csv": (False, ["ID oslony", "Typ", "Producent", "Numer katalogowy", "Srednica mm",
                           "Kolor", "Uwagi"], ["ID oslony", "Typ"]),
    "kable.csv": (False, ["ID kabla", "Producent", "Numer katalogowy", "Liczba zyl", "Ekran",
                          "Uwagi"], ["ID kabla"]),
    "etykiety.csv": (False, ["ID wiazki", "Tekst", "Wezel", "Odcinek", "Uwagi"],
                     ["ID wiazki", "Tekst"]),
    "uwagi.csv": (False, ["ID wiazki", "Nr", "Tekst", "Wezly"], ["ID wiazki", "Nr", "Tekst"]),
    "rewizje.csv": (False, ["ID wiazki", "Rewizja", "Data", "Autor", "Opis"],
                    ["ID wiazki", "Rewizja"]),
    "uklad.csv": (False, ["Wezel", "X mm", "Y mm"], ["Wezel", "X mm", "Y mm"]),
}


def czytaj_csv(sciezka):
    """Zwraca (naglowek, [(nr_wiersza, {kolumna: wartosc})]). Pomija puste i '#'."""
    with open(sciezka, encoding="utf-8-sig", newline="") as f:
        linie = f.read().splitlines()
    linie = [(i + 1, l) for i, l in enumerate(linie)
             if l.strip() and not l.lstrip().startswith("#")]
    if not linie:
        return [], []
    naglowek = [h.strip() for h in next(csv.reader([linie[0][1]], delimiter=";"))]
    wiersze = []
    for nr, l in linie[1:]:
        kom = next(csv.reader([l], delimiter=";"))
        wiersze.append((nr, {h: (kom[i].strip() if i < len(kom) else "")
                             for i, h in enumerate(naglowek)}))
    return naglowek, wiersze


def _liczba(d, zr, kolumna, v, typ=int):
    """'' / TODO / TBD -> None; liczba -> typ; smiec -> BLAD i None."""
    if v == "" or v.upper() in BRAKI:
        return None
    try:
        return typ(v.replace(" ", "").replace(",", "."))
    except ValueError:
        d.dodaj("BLAD", zr, f"{kolumna}: '{v}' nie jest liczba")
        return None


def _lista(v):
    return [x.strip() for x in v.split(",") if x.strip()]


def _unikalny(d, slownik, klucz, obj, zr, co):
    if klucz in slownik:
        d.dodaj("BLAD", zr, f"powtorzony {co} '{klucz}' (pierwszy: {slownik[klucz].zrodlo})")
        return
    slownik[klucz] = obj


def wczytaj(katalog) -> Dane:
    d = Dane()
    k = Path(katalog)
    t = {}
    for plik, (wymagany, kolumny, wymagane) in TABELE.items():
        t[plik] = []
        p = k / plik
        if not p.exists():
            if wymagany:
                d.dodaj("BLAD", plik, "brak wymaganego pliku")
            continue
        naglowek, wiersze = czytaj_csv(p)
        brak = [c for c in kolumny if c not in naglowek]
        if brak:
            d.dodaj("BLAD", plik, "brak kolumn: " + ", ".join(brak))
            continue
        for nr, w in wiersze:
            zr = f"{plik}:{nr}"
            puste = [c for c in wymagane if not w[c]]
            if puste:
                d.dodaj("BLAD", zr, "pusta kolumna wymagana: " + ", ".join(puste))
                continue
            for c in kolumny:
                if w[c].upper() in BRAKI:
                    d.dodaj("BRAK", zr, f"{c} = {w[c]}")
            t[plik].append((zr, w))
    _buduj(d, t)
    return d


def _buduj(d, t):
    for zr, w in t["parametry.csv"]:
        d.parametry[w["Parametr"]] = w["Wartosc"]
    if "naddatek_domyslny_mm" in d.parametry:
        d.naddatek_domyslny = _liczba(d, "parametry.csv", "naddatek_domyslny_mm",
                                      d.parametry["naddatek_domyslny_mm"]) or 0

    for zr, w in t["wiazki.csv"]:
        _unikalny(d, d.wiazki, w["ID wiazki"], Wiazka(
            w["ID wiazki"], w["Nazwa"], w["Numer rysunku"], w["Rewizja"],
            w["Miejsce montazu"], w["Uwagi"], zr), zr, "ID wiazki")

    for zr, w in t["wezly.csv"]:
        _unikalny(d, d.wezly, w["ID wezla"], Wezel(
            w["ID wezla"], w["ID wiazki"], w["Typ"].upper(), w["Opis"], w["Producent"],
            w["Numer katalogowy"], zr), zr, "ID wezla")

    for zr, w in t["odcinki.csv"]:
        _unikalny(d, d.odcinki, w["ID odcinka"], Odcinek(
            w["ID odcinka"], w["ID wiazki"], w["Wezel A"], w["Wezel B"],
            _liczba(d, zr, "Dlugosc mm", w["Dlugosc mm"]), _lista(w["Oslony"]),
            w["Uwagi"], zr), zr, "ID odcinka")

    for zr, w in t["zlacza.csv"]:
        _unikalny(d, d.zlacza, w["Oznaczenie"], Zlacze(
            w["Oznaczenie"], w["Urzadzenie"], w["Producent"], w["Obudowa"],
            _liczba(d, zr, "Liczba gniazd", w["Liczba gniazd"]), w["Styk"], w["Uszczelka"],
            w["Zaslepka"], w["Backshell"], _liczba(d, zr, "Naddatek mm", w["Naddatek mm"]),
            w["Widok czola"], w["Uwagi"], zr), zr, "Oznaczenie zlacza")

    for zr, w in t["przewody.csv"]:
        _unikalny(d, d.zyly, w["ID zyly"], Zyla(
            w["ID zyly"], w["Od zlacze"], w["Od gniazdo"], w["Do zlacze"], w["Do gniazdo"],
            w["Przekroj mm2"], w["Kolor"].upper(), w["Sygnal"], w["Typ przewodu"], w["Kabel"],
            w["Zyla w kablu"], w["Skrecona z"],
            _liczba(d, zr, "Naddatek mm", w["Naddatek mm"]) or 0, w["Uwagi"], zr),
            zr, "ID zyly")

    for zr, w in t["oslony.csv"]:
        _unikalny(d, d.oslony, w["ID oslony"], Oslona(
            w["ID oslony"], w["Typ"].upper(), w["Producent"], w["Numer katalogowy"],
            w["Srednica mm"], w["Kolor"], w["Uwagi"], zr), zr, "ID oslony")

    for zr, w in t["kable.csv"]:
        _unikalny(d, d.kable, w["ID kabla"], Kabel(
            w["ID kabla"], w["Producent"], w["Numer katalogowy"], w["Liczba zyl"],
            w["Ekran"], w["Uwagi"], zr), zr, "ID kabla")

    for zr, w in t["etykiety.csv"]:
        d.etykiety.append(Etykieta(w["ID wiazki"], w["Tekst"], w["Wezel"], w["Odcinek"], zr))
    for zr, w in t["uwagi.csv"]:
        d.uwagi.append(Uwaga(w["ID wiazki"], w["Nr"], w["Tekst"], _lista(w["Wezly"]), zr))
    for zr, w in t["rewizje.csv"]:
        d.rewizje.append(Rewizja(w["ID wiazki"], w["Rewizja"], w["Data"], w["Autor"],
                                 w["Opis"]))
    for zr, w in t["uklad.csv"]:
        x = _liczba(d, zr, "X mm", w["X mm"], float)
        y = _liczba(d, zr, "Y mm", w["Y mm"], float)
        if x is not None and y is not None:
            d.uklad[w["Wezel"]] = (x, y)
