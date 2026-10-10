# -*- coding: utf-8 -*-
"""
szablon.py - wstepnie wypelnione tabele wiazki (docs/54) z danych pinow 01/02.

    python -m wiazka.szablon [--dane docs/45_wireviz] [--wyjscie docs/45_wireviz/wiazki]
                             [--nadpisz]

Co jest PEWNE (z danych): urzadzenia, ich piny i sygnaly, cel kazdej zyly, gniazdo TTC
(kolumna "Pozycja w czesci"), kolor zyly (karta albo konwencja - jak na arkuszach strefowych).

Co jest ROBOCZE (do zastapienia przez usera) i jawnie tak oznaczone:
  - podzial na wiazki: jedna wiazka W-ROBOCZA na caly system,
  - topologia: TTC -> rozgalezienie na grupe funkcjonalna -> urzadzenie (gwiazda),
    wszystkie dlugosci TBD,
  - splice'y w miejsce wezlow zbiorczych XB_* (masa, +24 V, SGND, CAN) i pinow TTC,
    do ktorych idzie kilka zyl (fizycznie jedno gniazdo = jedna zyla).
    UWAGA CAN: splice to gwiazda - magistrala CAN musi byc LINIA (decyzja usera).

Czego NIE MA (TODO): obudowy wtyczek, producenci, liczba gniazd tam, gdzie karta jej nie
podaje, przekroje, typy przewodow. Nie zgadujemy - zasada projektu.
"""

import argparse
import datetime
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

TU = Path(__file__).resolve().parent
sys.path.insert(0, str(TU.parent))

import z_csv  # noqa: E402  (microdrive/z_csv.py - ta sama analiza co arkusze strefowe)
from kolory import zyla  # noqa: E402

WID = "W-ROBOCZA"
ROBOCZY = "ROBOCZY - do zastapienia"
TTC_GNIAZD = {"X1": 96, "X2": 58}
SZYNA_SPLICE = {  # (wezel zbiorczy, pin) -> (ID splice, opis)
    ("XB_GND", "0V"): ("SPL-GND", "masa 0 V / BAT- (punkt masy: DO DECYZJI)"),
    ("XB_SGND", "SGND"): ("SPL-SGND", "masa czujnikow SGND"),
    ("XB_24V", "24V"): ("SPL-24V", "+24 V stale zabezpieczone (bezpiecznik: TODO)"),
}


def _splice_szyny(wezel, pcel):
    if (wezel, pcel) in SZYNA_SPLICE:
        return SZYNA_SPLICE[(wezel, pcel)]
    m = re.match(r"XB_CAN(\d)$", wezel)
    if m:
        sufiks = {"H": "H", "L": "L", "EKRAN": "EKR"}.get(pcel, pcel)
        return (f"SPL-CAN{m.group(1)}-{sufiks}",
                f"CAN{m.group(1)} {pcel} - UWAGA: CAN ma byc LINIA, nie gwiazda (DO DECYZJI)")
    return (f"SPL-{wezel}-{pcel}", f"wezel zbiorczy {wezel} {pcel}")


def _liczba_gniazd(zlacze, prefiks=None):
    """Liczba gniazd z opisu zlacza karty, tylko gdy jednoznaczna; inaczej None."""
    t = zlacze or ""
    if prefiks:
        m = re.search(r"\b" + re.escape(prefiks) + r"\b[^,]*?(\d+)\s*-\s*pin", t, re.I)
        return int(m.group(1)) if m else None
    wzorce = [r"(\d+)\s*-\s*pin", r"\bDT[MP]?0[46]-(\d+)[PS]\b", r"(\d+)\s*-\s*biegun"]
    for w in wzorce:
        trafienia = set(re.findall(w, t, re.I))
        if len(trafienia) == 1:
            return int(trafienia.pop())
    return None


def _kolor_csv(kod):
    """'BNWH' (WireViz) -> 'BN/WH' (format docs/54)."""
    return kod if len(kod) <= 2 else f"{kod[:2]}/{kod[2:]}"


def zbuduj(dane):
    """Zwraca (tabele: nazwa -> (naglowek, wiersze), raport: [linie])."""
    a = z_csv.analizuj(Path(dane))
    pozycja = {}
    for r in a.piny:
        p = r["Pin"]
        pozycja[p] = ("X1" if p.startswith("P1") else "X2", (r.get("Pozycja w czesci") or "").strip())

    wezly = OrderedDict()   # id -> (typ, opis, producent, pn)
    zlacza = OrderedDict()  # id -> wiersz
    rodzic = {}             # wezel -> galaz (topologia robocza)
    raport = []

    for czesc in ("X1", "X2"):
        zid = f"TTC-{czesc}"
        wezly[zid] = ("ZLACZE", f"HY-TTC 510 czesc {czesc}", "", "")
        zlacza[zid] = [zid, "HY-TTC 510", "TTControl", "TODO", str(TTC_GNIAZD[czesc]),
                       "", "", "", "", "", "",
                       "wtyczka TTC (KOSTAL MLK 1.2 / SLK 2.8 wg pinu) - numer obudowy TODO"]
        rodzic[zid] = "B-TTC"
    wezly["B-TTC"] = ("ROZGALEZIENIE", f"wyjscie wiazki od TTC510 ({ROBOCZY})", "", "")

    def wezel_urzadzenia(dev, pin):
        """(id wezla zlacza, gniazdo) dla pinu urzadzenia; M2 'P1:2' -> ('M2-P1', '2')."""
        m = a.dev_meta[dev]
        baza = z_csv.bezpieczne(dev)
        pin = str(pin)
        pref = None
        if ":" in pin:
            pre, reszta = (x.strip() for x in pin.split(":", 1))
            if re.search(r"\b" + re.escape(pre) + r"\b", m["zlacze"] or ""):
                pref, pin = pre, reszta
        zid = f"{baza}-{pref}" if pref else baza
        if zid not in zlacza:
            g = a.grupa_dev.get(dev, "0")
            galaz = f"B-G{g}"
            if galaz not in wezly:
                nazwa = z_csv.NAZWY_GRUP.get(g, "do_ustalenia").replace("_", " ")
                wezly[galaz] = ("ROZGALEZIENIE", f"grupa {g}: {nazwa} ({ROBOCZY})", "", "")
                rodzic[galaz] = "B-TTC"
            wezly[zid] = ("ZLACZE", (m["type"] or dev)[:60], "", "")
            n = _liczba_gniazd(m["zlacze"], pref)
            uw = f"z karty: zlacze urzadzenia '{m['zlacze']}'"
            if m.get("wtyczka"):
                uw += f"; wtyczka '{m['wtyczka']}'"
            zlacza[zid] = [zid, dev + (f" {pref}" if pref else ""), "TODO", "TODO",
                           str(n) if n else "TODO", "", "", "", "", "", "", uw]
            rodzic[zid] = galaz
        return zid, pin

    def splice(sid, opis):
        if sid not in wezly:
            wezly[sid] = ("SPLICE", f"{opis} ({ROBOCZY})", "TODO", "TODO")
            rodzic[sid] = "B-TTC"
        return sid

    # 1. konce zyl z danych
    surowe = []  # [od_wezel, od_gn, do_wezel, do_gn, kolor, sygnal, uwagi]
    nr_dev = {d: i for i, d in enumerate(a.dev_meta)}
    piny_szyn = defaultdict(set)  # splice -> piny TTC wskazane jednoznacznie w tekscie celu
    for (dev, pin, rodzaj, wezel, pcel, syg, kod, zk), tekst in zip(a.polaczenia_sur, a.zrodla):
        od, od_gn = wezel_urzadzenia(dev, pin)
        kolor = _kolor_csv(zyla(kod, nr_dev[dev], zk))
        if rodzaj == "ttc":
            czesc, poz = pozycja[pcel]
            surowe.append([od, od_gn, f"TTC-{czesc}", poz, kolor, f"{syg} ({pcel})".strip(), pcel])
        else:
            sid, opis = _splice_szyny(wezel, pcel)
            splice(sid, opis)
            surowe.append([od, od_gn, sid, "", kolor, syg, ""])
            ttc_w_tekscie = set(re.findall(r"P\d{3}", tekst))
            if len(ttc_w_tekscie) == 1:
                piny_szyn[sid] |= ttc_w_tekscie

    # 2. gniazdo TTC z kilkoma zylami -> splice + jedna zyla do TTC
    licz = Counter(z[6] for z in surowe if z[6])
    for z in surowe:
        if z[6] and licz[z[6]] > 1:
            sid = splice(f"SPL-{z[6]}", f"rozgalezienie pinu TTC {z[6]} ({licz[z[6]]} zyl)")
            piny_szyn[sid].add(z[6])
            z[2], z[3] = sid, ""
    for sid, piny in sorted(piny_szyn.items()):
        if len(piny) > 1:
            raport.append(f"{sid}: wskazane rozne piny TTC {sorted(piny)} - polaczenie z TTC TODO")
            continue
        p = next(iter(piny))
        czesc, poz = pozycja[p]
        kol = next(z[4] for z in surowe if z[2] == sid).split("/")[0]
        surowe.append([sid, "", f"TTC-{czesc}", poz, kol, f"{sid} -> {p}", ""])
    for sid in [w for w, v in wezly.items() if v[0] == "SPLICE" and w not in piny_szyn]:
        raport.append(f"{sid}: brak pinu TTC w danych (masa/zasilanie poza TTC?) - cel TODO")

    # 3. liczba gniazd z opisu karty tylko, gdy zgodna z numerami pinow.
    # "M12 3-pin" (ifm IGM200) uzywa pinow 1, 3, 4 - opis liczy STYKI, nie pozycje.
    for zid, w in zlacza.items():
        if not w[4].isdigit() or zid.startswith("TTC-"):
            continue
        numery = [int(z[1]) for z in surowe if z[0] == zid and str(z[1]).isdigit()]
        numery += [int(z[3]) for z in surowe if z[2] == zid and str(z[3]).isdigit()]
        if numery and max(numery) > int(w[4]):
            raport.append(f"{zid}: opis karty mowi {w[4]} styki, a uzyty jest pin {max(numery)} "
                          "- liczba gniazd TODO (sprawdzic numeracje zlacza)")
            w[11] += f"; opis '{w[4]} styki' sprzeczny z numerem pinu {max(numery)}"
            w[4] = "TODO"

    # 4. tabele
    dzis = datetime.date.today().isoformat()
    przewody = [[f"W{i:03d}", z[0], z[1], z[2], z[3], "TODO", z[4], z[5], "", "", "", "", "", ""]
                for i, z in enumerate(surowe, 1)]
    odcinki = [[f"S{i:03d}", WID, rodzic[w], w, "TBD", "", ROBOCZY]
               for i, w in enumerate([w for w in wezly if w in rodzic], 1)]
    tabele = {
        "wiazki.csv": (["ID wiazki", "Nazwa", "Numer rysunku", "Rewizja", "Miejsce montazu",
                        "Uwagi"],
                       [[WID, "Wiazka robocza - caly system (podzial fizyczny DO USTALENIA)",
                         "", "0", "TODO", "szablon z danych 01/02; podzial na wiazki fizyczne "
                         "i topologia do wpisania"]]),
        "parametry.csv": (["Parametr", "Wartosc", "Uwagi"],
                          [["naddatek_domyslny_mm", "TODO", "do ustalenia z wiazkarnia"]]),
        "wezly.csv": (["ID wezla", "ID wiazki", "Typ", "Opis", "Producent", "Numer katalogowy"],
                      [[w, WID, t, o, pr, pn] for w, (t, o, pr, pn) in wezly.items()]),
        "odcinki.csv": (["ID odcinka", "ID wiazki", "Wezel A", "Wezel B", "Dlugosc mm",
                         "Oslony", "Uwagi"], odcinki),
        "zlacza.csv": (["Oznaczenie", "Urzadzenie", "Producent", "Obudowa", "Liczba gniazd",
                        "Styk", "Uszczelka", "Zaslepka", "Backshell", "Naddatek mm",
                        "Widok czola", "Uwagi"], list(zlacza.values())),
        "przewody.csv": (["ID zyly", "Od zlacze", "Od gniazdo", "Do zlacze", "Do gniazdo",
                          "Przekroj mm2", "Kolor", "Sygnal", "Typ przewodu", "Kabel",
                          "Zyla w kablu", "Skrecona z", "Naddatek mm", "Uwagi"], przewody),
        "oslony.csv": (["ID oslony", "Typ", "Producent", "Numer katalogowy", "Srednica mm",
                        "Kolor", "Uwagi"], []),
        "kable.csv": (["ID kabla", "Producent", "Numer katalogowy", "Liczba zyl", "Ekran",
                       "Uwagi"], []),
        "etykiety.csv": (["ID wiazki", "Tekst", "Wezel", "Odcinek", "Uwagi"], []),
        "uwagi.csv": (["ID wiazki", "Nr", "Tekst", "Wezly"],
                      [[WID, "1", "TOPOLOGIA ROBOCZA (gwiazda) - nie odwzorowuje przebiegu "
                                  "wiazki na pojezdzie", "B-TTC"]]),
        "rewizje.csv": (["ID wiazki", "Rewizja", "Data", "Autor", "Opis"],
                        [[WID, "0", dzis, "szablon", "wstepne wypelnienie z danych pinow"]]),
    }
    for dev, pin, syg, powod in a.raport_bez_celu:
        raport.append(f"bez celu - nie wpisane: {dev} pin {pin} ({syg[:30]}) -> {powod[:50]}")
    return tabele, raport


def zapisz(tabele, raport, wyj, zrodlo):
    wyj = Path(wyj)
    wyj.mkdir(parents=True, exist_ok=True)
    naglowek = (f"# SZABLON wygenerowany {datetime.date.today().isoformat()} z {zrodlo} "
                "(wiazka/szablon.py) - pozycje ROBOCZE i TODO do uzupelnienia; format: docs/54\n")
    for plik, (kol, wiersze) in tabele.items():
        linie = [";".join(kol)] + [";".join(str(c).replace(";", ",") for c in w) for w in wiersze]
        (wyj / plik).write_text(naglowek + "\n".join(linie) + "\n", encoding="utf-8-sig")
    (wyj / "CZYTAJ_MNIE_szablon.txt").write_text(
        __doc__.strip() + "\n\nUWAGI GENERATORA:\n" + "\n".join("  " + r for r in raport) + "\n",
        encoding="utf-8")


def main(argv=None):
    korzen = TU.parents[2]
    ap = argparse.ArgumentParser(prog="python -m wiazka.szablon")
    ap.add_argument("--dane", default=str(korzen / "docs" / "45_wireviz"))
    ap.add_argument("--wyjscie", default=str(korzen / "docs" / "45_wireviz" / "wiazki"))
    ap.add_argument("--nadpisz", action="store_true",
                    help="nadpisz istniejace tabele (UWAGA: kasuje wpisane recznie dane)")
    a = ap.parse_args(argv)
    wyj = Path(a.wyjscie)
    if wyj.exists() and any(wyj.glob("*.csv")) and not a.nadpisz:
        print(f"{wyj} zawiera juz tabele - nie nadpisuje (wpisane dane by zginely). "
              "Uzyj --nadpisz albo innego --wyjscie.")
        return 2
    tabele, raport = zbuduj(a.dane)
    zapisz(tabele, raport, wyj, a.dane)
    n = {k: len(v[1]) for k, v in tabele.items()}
    print(f"szablon -> {wyj}: {n['zlacza.csv']} zlaczy, {n['przewody.csv']} zyl, "
          f"{n['wezly.csv']} wezlow, {n['odcinki.csv']} odcinkow; uwag: {len(raport)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
