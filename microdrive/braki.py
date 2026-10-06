# -*- coding: utf-8 -*-
"""
braki.py - przeglad kompletnosci wiazek microdrive.

Sprawdza Z OBU STRON, bo kazda lapie co innego:

  A. OD STRONY URZADZEN - wiersz pinu w karcie, ktory nie trafil na rysunek
     (brak celu, cel nieistniejacy jako wezel).
  B. OD STRONY STEROWNIKA - pin TTC510 oznaczony UZYWANY, do ktorego ZADNE
     urzadzenie sie nie odwoluje. Tego nie widac patrzac na karty urzadzen,
     a to wlasnie tedy ucieka brakujacy czujnik albo cewka.
  C. ZLACZA - urzadzenie narysowane elektrycznie, ale bez ustalonego zlacza
     i wtyczki = nie da sie zamowic wiazki.
  D. NUMERY PINOW - narysowane jako "?1, ?2", bo karta ich nie podaje.
  E. URZADZENIA NIEDOBRANE - typ nie jest jeszcze wybrany.

Uzycie:  python microdrive/braki.py
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

TU = Path(__file__).resolve().parent
sys.path.insert(0, str(TU))
DANE = TU.parents[1] / "docs" / "45_wireviz"

from z_csv import cel, rozbij_pin, baza_oz, zakres  # noqa: E402

K_DOKAD = "Dokad (TTC510:Pxxx = pin sterownika)"
RE_PIN = re.compile(r"P(\d{3})")
NIEDOBRANE = ("nie dobrany", "nie ustalony", "jeszcze nie dobrane", "niedobran")


def czytaj(n):
    with open(DANE / n, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    piny = czytaj("01_TTC510_piny.csv")
    urz = czytaj("02_urzadzenia_piny.csv")
    out = []

    def w(s=""):
        out.append(s)

    w("PRZEGLAD BRAKOW - WIAZKI MICRODRIVE")
    w("=" * 78)
    w()

    # --- A. od strony urzadzen --------------------------------------------
    bez_celu, zly_cel = [], []
    for r in urz:
        d = (r.get(K_DOKAD) or "").strip()
        rodzaj, _wezel, _p = cel(d)
        if rodzaj is not None:
            continue
        oz = (r.get("Oznaczenie") or "").strip()
        pin = (r.get("Pin urzadzenia") or "").strip()
        syg = (r.get("Sygnal") or "").strip()
        poz = (f"{oz} pin {pin or '?'} ({syg})", d or "(puste)")
        if not d or d.lower() in ("-", "nc", "niepodlaczony", "nie podlaczac"):
            bez_celu.append(poz)
        else:
            zly_cel.append(poz)

    w(f"A1. PINY URZADZEN CELOWO NIEUZYWANE ({len(bez_celu)})")
    w("    (karta ma pin, projekt go nie uzywa - to NIE jest brak)")
    w()
    w(f"A2. PINY Z CELEM, KTORY NIE JEST ZDEFINIOWANYM WEZLEM ({len(zly_cel)})")
    w("    To SA braki: cel nazwany slowem, ale takiego elementu nie ma na rysunku.")
    for opis, d in zly_cel:
        w(f"      {opis[:52]:52s} -> {d[:40]}")
    w()

    # --- B. od strony sterownika ------------------------------------------
    # Zbierz wszystkie piny TTC, do ktorych odwoluje sie jakiekolwiek urzadzenie.
    uzyte_przez_urzadzenia = set()
    for r in urz:
        for m in RE_PIN.finditer((r.get(K_DOKAD) or "")):
            uzyte_przez_urzadzenia.add("P" + m.group(1))

    sieroty = []
    for r in piny:
        if (r.get("Status") or "").strip() != "UZYWANY":
            continue
        p = (r.get("Pin") or "").strip()
        if p not in uzyte_przez_urzadzenia:
            sieroty.append((p, (r.get("Oznaczenie") or "").strip(),
                            (r.get("Urzadzenie / funkcja") or "").strip()))

    w(f"B. PINY TTC510 'UZYWANY' BEZ ZADNEGO URZADZENIA W KARTACH ({len(sieroty)})")
    w("   Sterownik ma funkcje na tym pinie, ale po drugiej stronie nic nie ma")
    w("   opisanego - wiazka nie moze powstac.")
    for p, oz, fun in sieroty:
        w(f"      {p}  {oz[:18]:18s} {fun[:48]}")
    w()

    # --- C/D/E. stan urzadzen ---------------------------------------------
    meta = {}
    for r in urz:
        oz_zb = (r.get("Oznaczenie") or "").strip()
        zl = (r.get("Zlacze urzadzenia") or "").strip()
        pin_raw = (r.get("Pin urzadzenia") or "").strip()
        lista = zakres(oz_zb) if ":" not in pin_raw else None
        devs = lista or [rozbij_pin(oz_zb, pin_raw, zl)[0]]
        for dev in devs:
            m = meta.setdefault(dev, {"zl": zl, "wt": (r.get("Wtyczka (odpowiednik)") or "").strip(),
                                      "typ": (r.get("Producent / typ") or "").strip(),
                                      "nazwa": (r.get("Urzadzenie") or "").strip(), "q": 0})
            if pin_raw in ("?", ""):
                m["q"] += 1

    brak_zlacza = [(d, v) for d, v in meta.items()
                   if "todo" in v["zl"].lower() or "todo" in v["wt"].lower()]
    niedobrane = [(d, v) for d, v in meta.items()
                  if any(x in (v["typ"] + " " + v["nazwa"]).lower() for x in NIEDOBRANE)]
    bez_numerow = [(d, v) for d, v in meta.items() if v["q"]]

    w(f"C. URZADZENIA BEZ USTALONEGO ZLACZA / WTYCZKI ({len(brak_zlacza)})")
    w("   Rysunek elektryczny jest, ale wiazki nie da sie zamowic.")
    for d, v in sorted(brak_zlacza):
        w(f"      {d:26s} zlacze='{v['zl'][:26]}' wtyczka='{v['wt'][:22]}'")
    w()
    w(f"D. URZADZENIA O NIEZNANYCH NUMERACH PINOW ({len(bez_numerow)})")
    w("   Na rysunku jako '?1, ?2' - wiadomo ILE zyl, nie wiadomo DOKAD w zlaczu.")
    for d, v in sorted(bez_numerow):
        w(f"      {d:26s} {v['q']} pin. bez numeru   {v['nazwa'][:34]}")
    w()
    w(f"E. URZADZENIA JESZCZE NIEDOBRANE ({len(niedobrane)})")
    for d, v in sorted(niedobrane):
        w(f"      {d:26s} {(v['typ'] or v['nazwa'])[:56]}")
    w()

    w("=" * 78)
    w(f"PODSUMOWANIE: {len(zly_cel)} braków celu (A2) · {len(sieroty)} osieroconych pinów TTC (B)")
    w(f"              {len(brak_zlacza)} bez złącza (C) · {len(bez_numerow)} bez numerów pinów (D)")
    w(f"              {len(niedobrane)} niedobranych urządzeń (E)")

    tekst = "\n".join(out)
    (TU.parent / "RAPORT_braki.txt").write_text(tekst, encoding="utf-8")
    print(tekst)


if __name__ == "__main__":
    main()
