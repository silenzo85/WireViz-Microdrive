# -*- coding: utf-8 -*-
"""
Scalanie arkuszy strefowych w jeden rysunek calosciowy.

PO CO TO ISTNIEJE:
Natywny mechanizm `-p/--prepend` w WireViz sklada pliki JAKO TEKST. Gdy dwa pliki
maja wlasna sekcje `connectors:`, YAML zostawia tylko OSTATNIA - pierwsza znika
bez zadnego ostrzezenia. Sprawdzone: sklejenie dwoch plikow po 1 zlaczu daje
1 zlacze, nie 2. Dla rysunku instalacji to cicha utrata polowy schematu.

Ten skrypt scala poprawnie:
  - `connectors` / `cables` - scalane po oznaczeniu,
  - `connections` - listy doklejane,
  - `metadata` / `options` / `tweak` - pozniejszy plik nadpisuje wczesniejszy,
  - `additional_bom_items` - doklejane.

KONFLIKTY sa bledem, nie cicha nadpisana. To samo oznaczenie moze wystapic
w kilku plikach TYLKO jesli definicja jest identyczna - tak wlasnie opisuje sie
zlacza graniczne (np. pierscien XR1 albo zlacza TTC510), ktore widac na kilku
arkuszach naraz.

Uzycie:
    python microdrive/zloz.py -o build/calosc.yml microdrive/strefa_*.yml
"""

import argparse
import sys
from pathlib import Path

import yaml

SEKCJE_SLOWNIKOWE = ("connectors", "cables")
SEKCJE_LISTOWE = ("connections", "additional_bom_items")
SEKCJE_NADPISYWANE = ("metadata", "options", "tweak")


def _scal_slownik(cel, nowy, sekcja, plik, zrodla, bledy):
    for oznaczenie, definicja in (nowy or {}).items():
        if oznaczenie in cel:
            if cel[oznaczenie] != definicja:
                bledy.append(
                    f"  {sekcja}/{oznaczenie}: rozne definicje w "
                    f"'{zrodla[(sekcja, oznaczenie)]}' i '{plik}'"
                )
            continue  # identyczna definicja = zlacze graniczne, OK
        cel[oznaczenie] = definicja
        zrodla[(sekcja, oznaczenie)] = plik


def scal(pliki):
    """Zwraca (dokument, lista_bledow)."""
    wynik = {}
    zrodla = {}
    bledy = []

    for sciezka in pliki:
        p = Path(sciezka)
        if not p.exists():
            bledy.append(f"  nie ma pliku: {p}")
            continue
        dane = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(dane, dict):
            bledy.append(f"  {p}: plik nie jest slownikiem YAML")
            continue

        for sekcja in SEKCJE_SLOWNIKOWE:
            if sekcja in dane:
                wynik.setdefault(sekcja, {})
                _scal_slownik(wynik[sekcja], dane[sekcja], sekcja, p.name, zrodla, bledy)

        for sekcja in SEKCJE_LISTOWE:
            if sekcja in dane:
                wynik.setdefault(sekcja, []).extend(dane[sekcja] or [])

        for sekcja in SEKCJE_NADPISYWANE:
            if sekcja in dane:
                wynik.setdefault(sekcja, {}).update(dane[sekcja] or {})

        nieznane = set(dane) - set(
            SEKCJE_SLOWNIKOWE + SEKCJE_LISTOWE + SEKCJE_NADPISYWANE
        )
        for sekcja in sorted(nieznane):
            bledy.append(f"  {p.name}: nieznana sekcja '{sekcja}' - pominieta")

    return wynik, bledy


def sprawdz_spojnosc(dok):
    """Polaczenia wskazujace na nieistniejace oznaczenia."""
    znane = set(dok.get("connectors", {})) | set(dok.get("cables", {}))
    brakujace = set()
    for polaczenie in dok.get("connections", []):
        for ogniwo in polaczenie or []:
            if isinstance(ogniwo, dict):
                brakujace |= {k for k in ogniwo if k not in znane}
    return sorted(brakujace)


def main():
    ap = argparse.ArgumentParser(description="Scala arkusze strefowe WireViz.")
    ap.add_argument("pliki", nargs="+", help="pliki YAML stref (kolejnosc ma znaczenie)")
    ap.add_argument("-o", "--output", required=True, help="plik wynikowy YAML")
    args = ap.parse_args()

    dok, bledy = scal(args.pliki)

    if bledy:
        print("KONFLIKTY / PROBLEMY:", file=sys.stderr)
        print("\n".join(bledy), file=sys.stderr)
        return 1

    brakujace = sprawdz_spojnosc(dok)
    if brakujace:
        print(
            "Polaczenia wskazuja na nieistniejace oznaczenia: "
            + ", ".join(brakujace),
            file=sys.stderr,
        )
        print(
            "Zdefiniuj je w arkuszu albo dodaj plik z definicjami zlacz granicznych.",
            file=sys.stderr,
        )
        return 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(dok, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    print(
        f"Scalono {len(args.pliki)} ark. -> {out}  "
        f"({len(dok.get('connectors', {}))} zlacz, "
        f"{len(dok.get('cables', {}))} kabli, "
        f"{len(dok.get('connections', []))} polaczen)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
