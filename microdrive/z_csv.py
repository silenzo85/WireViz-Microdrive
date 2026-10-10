# -*- coding: utf-8 -*-
"""
z_csv.py - buduje arkusze WireViz z pakietu danych projektu microdrive.

Zrodlo: docs/45_wireviz/*.csv, generowane przez
        driver_sil2/tools/gen_wireviz_dane.py (drzewo eksportu + kod + karty urzadzen).
Wynik:  microdrive/_wspolne.yml + microdrive/strefa_*.yml

Dlaczego generator, a nie recznie pisany YAML: architektura projektu wciaz sie
zmienia. Kazda zmiana w pinoucie ma przejsc przez regeneracje, nie przez recznego
diffa na rysunku.

NIC NIE JEST ZMYSLANE. Pin bez danych trafia na rysunek jako "?" albo z adnotacja
TODO; polaczenie bez ustalonego celu nie jest rysowane, tylko wypisane w raporcie.

Uzycie:
    python microdrive/z_csv.py
    python microdrive/z_csv.py --dane "C:/.../docs/45_wireviz"
"""

import argparse
import csv
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from types import SimpleNamespace

import yaml

from kolory import LEGENDA, kolor, zyla

TU = Path(__file__).resolve().parent
sys.path.insert(0, str(TU))
DANE_DOMYSLNE = TU.parents[1] / "docs" / "45_wireviz"

K_DOKAD = "Dokad (TTC510:Pxxx = pin sterownika)"
RE_PIN = re.compile(r"P(\d{3})")

# Cele, ktore NIE sa polaczeniem do narysowania. Kazdy trafia do raportu.
NIEPODLACZONE = {
    "", "-", "nc", "niepodlaczony", "todo_hardware", "nie podlaczac",
}

# Magistrale i szyny modelowane jako wezly zbiorcze. To konwencja RYSUNKOWA
# (CAN jest multidrop, masa jest szyna) - nie wymysl elektryczny.
SZYNY = OrderedDict([
    ("XB_CAN0", "Magistrala CAN0 - operator (250 kbit/s)"),
    ("XB_CAN1", "Magistrala CAN1 - Bodybuilder-CAN pojazdu (250 kbit/s)"),
    ("XB_CAN2", "Magistrala CAN2 - rezerwa / diagnostyka"),
    ("XB_24V", "Szyna +24 V zabezpieczona (bezpiecznik: DO USTALENIA)"),
    ("XB_GND", "Szyna 0 V / BAT-"),
    ("XB_SGND", "Masa czujnikow (SGND)"),
])

NAZWY_GRUP = {
    "1": "naped_hydrostatyczny",
    "2": "mercedes",
    "3": "hamulec_zasadniczy",
    "4": "lapy_podporowe",
    "5": "skret",
    "6": "obrotnica",
    "7": "bezpieczenstwo",
    "8": "operator_sygnalizacja",
    "9": "zasilanie",
    "10": "magistrale_can",
}


def czytaj(sciezka):
    with open(sciezka, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


# --- rozbior pola "Dokad" ----------------------------------------------------


def zawin(t, n=90, maks=8):
    """
    Uwagi lamane w linie po ~90 znakow zamiast docinania do 200.
    Docinanie gubilo koncowke - np. uwaga o diodzie 1N4001 i POLARYZACJI
    zaworu YCL zaczyna sie ok. 230. znaku i znikala z rysunku.
    """
    out, cur = [], ""
    for slowo in str(t or "").split():
        if len(cur) + 1 + len(slowo) <= n:
            cur = (cur + " " + slowo).strip()
        else:
            if cur:
                out.append(cur)
            cur = slowo
    if cur:
        out.append(cur)
    if len(out) > maks:
        out = out[:maks]
        out[-1] += " ..."
    return chr(10).join(out)


def esc(t):
    """
    Tekst z CSV to DANE, nie markup. WireViz wstawia opisy wprost do etykiet
    HTML graphviza (typ MultilineHypertext dopuszcza tam HTML celowo), wiec
    goly '>=' w uwadze wywala render: "syntax error near '='".
    Escape robimy u SIEBIE, zeby nie zmieniac zachowania upstreamu.
    """
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def norm_pin(p):
    """
    Dopasowanie do wv_helper.expand() WireViz:
      - napis numeryczny jest tam zamieniany na int -> musimy podac int, inaczej
        'BA1:1 not found' (porownanie 1 in ['1',...] = False),
      - napis "liczba-liczba" jest traktowany jako ZAKRES (11-12 -> 11, 12),
        wiec TYLKO wtedy myslnik zamieniamy na '/'.
    Gol y '-' (zacisk minus) przechodzi przez expand() bez zmian - zamiana go
    na '/' zgubila oznaczenie bieguna na zaworze YCL, gdzie polaryzacja jest
    istotna (dioda 1N4001 we wtyczce). Sprawdzone na wv_helper.expand.
    """
    p = str(p).strip()
    if p.isdigit():
        return int(p)
    a, kreska, b = p.partition("-")
    if kreska and a.strip().isdigit() and b.strip().isdigit():
        return p.replace("-", "/")
    return p or "?"


def cel(tekst):
    """Zwraca (rodzaj, wezel, pin) albo (None, powod, None)."""
    t = (tekst or "").strip()
    low = t.lower()
    if low in NIEPODLACZONE or low.startswith("todo_hardware"):
        return None, t or "(puste)", None

    # Masy najpierw - "0 V CAN0 (BAT-)" to masa, nie magistrala.
    if re.search(r"\b0 ?v\b|\bbat-|\bmasa\b|\bgnd\b", low) and "sgnd" not in low:
        return "szyna", "XB_GND", "0V"

    # Magistrala TYLKO gdy celem jest sama szyna (CAN0-H / CAN0-L / "CAN0 (" /
    # ekran). "TTC510:P155 (+24 V CAN0)" to PIN ZASILANIA, nie magistrala.
    m = re.search(r"CAN(\d)\s*-\s*(H|L)|CAN(\d)\s*\(|ekran\s+CAN(\d)", t, re.I)
    if m:
        nr = m.group(1) or m.group(3) or m.group(4)
        szyna = f"XB_CAN{nr}"
        if "ekran" in low or "shield" in low:
            return "szyna", szyna, "EKRAN"
        if m.group(2):
            return "szyna", szyna, m.group(2).upper()
        return "szyna", szyna, "H"

    if "sgnd" in low:
        return "szyna", "XB_SGND", "SGND"
    if re.search(r"\bbat-|\b0 ?v\b|masa|\bgnd\b", low):
        return "szyna", "XB_GND", "0V"

    m = RE_PIN.search(t)
    if m:
        n = int(m.group(1))
        return "ttc", ("X1" if n < 200 else "X2"), f"P{n}"

    # "+24 V (STALE) zabezpieczone (TODO: bezpiecznik)" - cel jest OKRESLONY:
    # stale zasilanie przez bezpiecznik. Niewiadoma jest tylko wartosc
    # bezpiecznika - to idzie do uwagi szyny, a nie jest powodem, zeby zyly
    # nie rysowac. Bez tego SQ1/SQ2/BQ3/obrotnica wychodzily na rysunku BEZ
    # zasilania (FIX32: zasilanie stale, NIE z P152).
    if "+24" in t and re.search(r"zabezpiecz|bezpiecznik", low):
        return "szyna", "XB_24V", "24V"

    return None, t, None


RE_ZAKRES = re.compile(r"^([A-Za-z_-]+)(\d+)\.\.([A-Za-z_-]*)(\d+)$")


def baza_oz(oz):
    """'M2 (silnik skretu)' -> 'M2';  'SQ1, SQ2' -> 'SQ1_SQ2'."""
    oz = (oz or "").strip()
    oz = oz.split("(")[0].strip()
    return "_".join(x.strip() for x in oz.split(",") if x.strip()) or "X"


def zakres(oz):
    """'BP1..BP6' -> ['BP1'...'BP6'];  inne -> None."""
    m = RE_ZAKRES.match((oz or "").strip())
    if not m:
        return None
    pre, a, _pre2, b = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    return [f"{pre}{i}" for i in range(a, b + 1)] if b >= a else None


def rozbij_pin(oznaczenie, pin, zlacze):
    """
    'YV1a:1' -> ('YV1a', '1')        - prefiks to OSOBNE urzadzenie
    'P1:1'   -> ('M2', 'P1:1')       - prefiks to ZLACZE tego samego urzadzenia
    Rozroznienie po polu "Zlacze urzadzenia": jesli prefiks tam wystepuje,
    to nazwa zlacza (M2 ma P1/P2/P3), a nie drugie urzadzenie.
    """
    pin = (pin or "").strip()
    baza = baza_oz(oznaczenie)
    if ":" in pin:
        pre, reszta = (x.strip() for x in pin.split(":", 1))
        if re.search(r"\b" + re.escape(pre) + r"\b", zlacze or ""):
            return baza, pin           # prefiks = zlacze urzadzenia
        return pre, reszta             # prefiks = osobne urzadzenie
    return baza, pin or "?"


PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
                   "acelnoszzACELNOSZZ")


def bezpieczne(oz):
    """Oznaczenie na bezpieczny identyfikator YAML/graphviz."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", oz.strip().translate(PL))
    return s.strip("_") or "X"


def uwaga_kolorow(polaczenia_kabla):
    """Mowi wprost, ktore kolory sa z karty, a ktore z konwencji rysunkowej."""
    zk = sum(1 for *_x, _k, flaga in polaczenia_kabla if flaga)
    n = len(polaczenia_kabla)
    if zk == n:
        return "Kolory zyl wg karty urzadzenia. Dlugosc DO USTALENIA."
    if zk == 0:
        return ("Kolory zyl wg KONWENCJI FUNKCYJNEJ (karta ich nie podaje) - "
                "do zatwierdzenia przed zamowieniem wiazki. Dlugosc DO USTALENIA.")
    return (f"Kolory: {zk} z {n} zyl wg karty, reszta wg konwencji funkcyjnej "
            "- do zatwierdzenia. Dlugosc DO USTALENIA.")


def dodaj(dev_meta, dev_piny, polaczenia, raport, dev, pin, syg, dokad, r, zlacze, uwagi, oz_zb,
          zrodla=None):
    """Dopisuje jeden pin urzadzenia i jego polaczenie (albo brak celu)."""
    if dev not in dev_meta:
        dev_meta[dev] = {
            "type": (r.get("Urzadzenie") or "").strip(),
            "subtype": (r.get("Producent / typ") or "").strip(),
            "zlacze": zlacze,
            "uwagi": uwagi,
            "zbior": oz_zb,
            "wtyczka": (r.get("Wtyczka (odpowiednik)") or "").strip(),
        }
    pin = norm_pin(pin)
    istniejace = [p for _d, p, _s in dev_piny[dev]]
    if pin == "?":
        # Karta nie podaje numeru pinu. Bez numerowania WSZYSTKIE takie sygnaly
        # jednego urzadzenia skleilyby sie w jeden pin i na rysunku zostalaby
        # tylko pierwsza etykieta (SQ1/SQ2: 4 sygnaly -> 1 pin).
        pin = f"?{sum(1 for x in istniejace if str(x).startswith('?')) + 1}"
    if pin not in istniejace:
        dev_piny[dev].append((dev, pin, syg))

    rodzaj, wezel, pcel = cel(dokad)
    if rodzaj is None:
        raport.append((dev, pin, syg, wezel))
        return
    kod, zk = kolor(syg, r.get("Kolor zyly (karta)"), cel_to_pin_ttc=(rodzaj == "ttc"))
    polaczenia.append((dev, pin, rodzaj, wezel, pcel, syg, kod, zk))
    if zrodla is not None:  # oryginalny tekst celu (szablon wiazek: pin TTC magistrali)
        zrodla.append((dokad or "").strip())


def analizuj(dane):
    """
    Rozbior danych 01/02 na urzadzenia, piny i polaczenia (kroki 1-3).
    Wspolny dla arkuszy strefowych (main) i szablonu tabel wiazek
    (wiazka/szablon.py) - obie drogi musza czytac kolumne "Dokad" identycznie.
    """
    piny = czytaj(dane / "01_TTC510_piny.csv")
    urz = czytaj(dane / "02_urzadzenia_piny.csv")

    # --- 1. zlacza TTC510 ---------------------------------------------------
    ttc = {
        "X1": {"type": "HY-TTC 510", "subtype": "czesc X1, 96-pin (lewa), styki KOSTAL MLK 1.2",
               "pins": [], "pinlabels": [], "hide_disconnected_pins": True},
        "X2": {"type": "HY-TTC 510", "subtype": "czesc X2, 58-pin (prawa), MLK 1.2 / SLK 2.8",
               "pins": [], "pinlabels": [], "hide_disconnected_pins": True},
    }
    grupa_pinu, opis_pinu = {}, {}
    for r in piny:
        p = r["Pin"]
        czesc = "X1" if p.startswith("P1") else "X2"
        ttc[czesc]["pins"].append(p)
        oz = (r.get("Oznaczenie") or "").strip()
        fun = (r.get("Urzadzenie / funkcja") or "").strip()
        ttc[czesc]["pinlabels"].append(esc(oz or fun[:28] or r.get("Status", "")))
        g = (r.get("Grupa funkcjonalna") or "").strip()
        grupa_pinu[p] = g.split(" ", 1)[0] if g else ""
        opis_pinu[p] = oz or fun

    # --- 2. urzadzenia ------------------------------------------------------
    dev_meta, dev_piny = OrderedDict(), defaultdict(list)
    polaczenia_sur = []          # (dev, pin_dev, rodzaj, wezel, pin_celu, sygnal)
    raport_bez_celu = []
    zrodla = []                  # rownolegle do polaczenia_sur: tekst "Dokad"

    # Zbiorcze "B-SLEW1, B-SLEW2": jesli ten sam numer pinu wystepuje tyle razy,
    # ilu jest czlonkow, to sa ODDZIELNE urzadzenia (kolejne wiersze = kolejni
    # czlonkowie), a piny jednokrotne sa wspolne dla wszystkich. Bez tego dwa
    # czujniki M12 3-pin rysowaly sie jako jeden klocek z dwoma wyjsciami na
    # pinie 4 - fizycznie niemozliwe. Piny "?" i z prefiksem "X:" pomijane.
    przydzial = {}
    grupy = defaultdict(list)
    for i, r in enumerate(urz):
        grupy[(r.get("Oznaczenie") or "").strip()].append(i)
    for oz, idx in grupy.items():
        czlonki = [x.strip() for x in oz.split("(")[0].split(",") if x.strip()]
        if len(czlonki) < 2:
            continue
        piny_gr = [(urz[i].get("Pin urzadzenia") or "").strip() for i in idx]
        if any(pg in ("", "?") or ":" in pg for pg in piny_gr):
            continue
        licz = Counter(piny_gr)
        powt = [pg for pg, n in licz.items() if n > 1]
        if not powt or any(licz[pg] != len(czlonki) for pg in powt):
            continue
        uzyte = Counter()
        for i, pg in zip(idx, piny_gr):
            if licz[pg] == len(czlonki):
                przydzial[i] = [czlonki[uzyte[pg]]]
                uzyte[pg] += 1
            else:
                przydzial[i] = czlonki

    # "-" w kolumnie pinu bywa DWOJAKO: zacisk minus (YCL: "+" i "-") albo
    # "numeru brak" (HOLD/silownik: cztery wiersze, wszystkie "-"). Powtorzony
    # "-" w obrebie jednego oznaczenia = brak numeru -> traktujemy jak "?",
    # inaczej wszystkie sygnaly (tu: oba kanaly deadmana + silownik) skleilyby
    # sie w jeden pin. Pojedynczy "-" zostaje zaciskiem minus.
    minus_jako_brak = {oz for oz, idx in grupy.items()
                       if sum(1 for i in idx
                              if (urz[i].get("Pin urzadzenia") or "").strip() == "-") > 1}

    for nr_wiersza, r in enumerate(urz):
        if ((r.get("Oznaczenie") or "").strip() in minus_jako_brak
                and (r.get("Pin urzadzenia") or "").strip() == "-"):
            r = dict(r, **{"Pin urzadzenia": "?"})
        oz_zb = (r.get("Oznaczenie") or "").strip()
        if nr_wiersza in przydzial:
            for d in przydzial[nr_wiersza]:
                dodaj(dev_meta, dev_piny, polaczenia_sur, raport_bez_celu,
                      d, (r.get("Pin urzadzenia") or "").strip(),
                      (r.get("Sygnal") or "").strip(), r.get(K_DOKAD), r,
                      (r.get("Zlacze urzadzenia") or "").strip(),
                      (r.get("Uwagi do urzadzenia") or "").strip(), oz_zb, zrodla)
            continue
        zlacze = (r.get("Zlacze urzadzenia") or "").strip()
        syg = (r.get("Sygnal") or "").strip()
        uwagi = (r.get("Uwagi do urzadzenia") or "").strip()
        pin_raw = (r.get("Pin urzadzenia") or "").strip()

        # Zakres "BP1..BP6" rozwijamy na osobne urzadzenia TYLKO gdy wiersze nie
        # sa juz rozbite prefiksem (YV1a:1 itp.).
        lista = zakres(oz_zb) if ":" not in pin_raw else None
        if lista:
            cele = [c.strip() for c in (r.get(K_DOKAD) or "").split("/")]
            for i, d in enumerate(lista):
                dc = cele[i] if len(cele) == len(lista) else (r.get(K_DOKAD) or "")
                dodaj(dev_meta, dev_piny, polaczenia_sur, raport_bez_celu,
                      d, pin_raw or "?", syg, dc, r, zlacze, uwagi, oz_zb, zrodla)
            continue

        dev, pin = rozbij_pin(oz_zb, pin_raw, zlacze)
        # "YVx:2" = zacisk WSPOLNY dla wszystkich YV (powrot cewki na 0 V).
        # Wczesniej byl pomijany - kazda cewka miala na rysunku tylko jeden
        # przewod, bez powrotu.
        if dev.lower().endswith("x") and ":" in pin_raw:
            pref = dev[:-1]
            rodzina = [d for d in dev_meta if d.startswith(pref)]
            for d in rodzina:
                dodaj(dev_meta, dev_piny, polaczenia_sur, raport_bez_celu,
                      d, pin, syg, r.get(K_DOKAD), r, zlacze, uwagi, oz_zb, zrodla)
            if not rodzina:
                raport_bez_celu.append((dev, pin, syg, "brak urzadzen pasujacych do " + pref))
            continue
        dodaj(dev_meta, dev_piny, polaczenia_sur, raport_bez_celu,
              dev, pin, syg, r.get(K_DOKAD), r, zlacze, uwagi, oz_zb, zrodla)

    # --- 3. przypisanie urzadzen do grup -----------------------------------
    grupa_dev = {}
    for dev in dev_meta:
        glosy = defaultdict(int)
        for d, _pd, rodzaj, wezel, pcel, _s, _k, _zk in polaczenia_sur:
            if d == dev and rodzaj == "ttc":
                glosy[grupa_pinu.get(pcel, "")] += 1
        # Piny zasilania (gr. 9) i CAN (gr. 10) ma prawie kazde urzadzenie -
        # nie moga przeglosowac pinu funkcyjnego. Licza sie dopiero gdy nic innego nie ma.
        funkcyjne = {g: n for g, n in glosy.items() if g not in ("", "9", "10")}
        if funkcyjne:
            grupa_dev[dev] = max(funkcyjne, key=funkcyjne.get)
            continue
        if glosy:
            grupa_dev[dev] = max(glosy, key=glosy.get)
            continue
        # brak pinu TTC - przypisz po magistrali (wezly CAN maja tylko szyne)
        szyny_dev = {w for d, _p, rodz, w, _pc, _s, _k, _zk in polaczenia_sur
                     if d == dev and rodz == "szyna"}
        if "XB_CAN1" in szyny_dev:
            grupa_dev[dev] = "2"      # Bodybuilder-CAN = Mercedes
        elif szyny_dev & {"XB_CAN0", "XB_CAN2"}:
            grupa_dev[dev] = "10"     # magistrala operatora
        else:
            grupa_dev[dev] = "0"
    return SimpleNamespace(piny=piny, urz=urz, ttc=ttc, grupa_pinu=grupa_pinu,
                           opis_pinu=opis_pinu, dev_meta=dev_meta, dev_piny=dev_piny,
                           polaczenia_sur=polaczenia_sur,
                           raport_bez_celu=raport_bez_celu, grupa_dev=grupa_dev,
                           zrodla=zrodla)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dane", default=str(DANE_DOMYSLNE))
    ap.add_argument("--wyjscie", default=str(TU))
    a = ap.parse_args()

    dane, wyj = Path(a.dane), Path(a.wyjscie)
    if not (dane / "01_TTC510_piny.csv").exists():
        sys.exit(f"Brak danych w {dane}. Uruchom najpierw driver_sil2/tools/gen_wireviz_dane.py")

    a_ = analizuj(dane)
    ttc, grupa_pinu, dev_meta, dev_piny = a_.ttc, a_.grupa_pinu, a_.dev_meta, a_.dev_piny
    polaczenia_sur, raport_bez_celu, grupa_dev = a_.polaczenia_sur, a_.raport_bez_celu, a_.grupa_dev

    # --- 4. szyny: ile pinow ------------------------------------------------
    # Piny szyn numerujemy (1,2,3...), a opis "SGND / SL1" idzie do etykiety.
    # Dluga nazwa pinu wychodzi poza kolumne numeru i wchodzi pod zyly.
    szyna_piny = defaultdict(list)       # wezel -> [(nr, etykieta)]
    szyna_idx = {}                       # (wezel, pcel, dev) -> nr
    for dev, pd, rodzaj, wezel, pcel, _s, _k, _zk in polaczenia_sur:
        if rodzaj == "szyna":
            k = (wezel, pcel, dev)
            if k not in szyna_idx:
                nr = len(szyna_piny[wezel]) + 1
                szyna_idx[k] = nr
                szyna_piny[wezel].append((nr, f"{pcel} / {dev}"))

    wspolne = {"connectors": {}}
    for k in ("X1", "X2"):
        wspolne["connectors"][k] = ttc[k]
    for s, op in SZYNY.items():
        if szyna_piny[s]:
            wspolne["connectors"][s] = {
                "type": op, "subtype": "wezel zbiorczy (konwencja rysunkowa)",
                "pins": [nr for nr, _e in szyna_piny[s]],
                "pinlabels": [esc(e) for _nr, e in szyna_piny[s]],
                "hide_disconnected_pins": True,
            }

    bazy = {k for *_x, k, _zk in polaczenia_sur}   # baza bez paska
    wspolne["metadata"] = {
        "legenda_kolorow": [f"{k} = {o}" for k, o in LEGENDA if k in bazy]
        + ["-- drugi kolor (pasek) = numer przebiegu, nie funkcja --"]
    }

    naglowek = ("# PLIK GENEROWANY - nie edytowac recznie.\n"
                "# Zrodlo: docs/45_wireviz/*.csv  ->  microdrive/z_csv.py\n")
    (wyj / "_wspolne.yml").write_text(
        naglowek + "# Zlacza TTC510 + szyny zbiorcze (CAN, masy), widoczne na kazdym arkuszu.\n"
        + yaml.safe_dump(wspolne, sort_keys=False, allow_unicode=True), encoding="utf-8")

    # --- 5. arkusze strefowe ------------------------------------------------
    for stary in wyj.glob("strefa_*.yml"):
        stary.unlink()

    # WireViz tworzy tylko zlacza wystepujace w polaczeniach. Urzadzenie bez
    # ani jednego ustalonego celu nie da sie narysowac - trafia do raportu.
    maja_polaczenia = {d for d, *_ in polaczenia_sur}
    bez_polaczen = [d for d in dev_meta if d not in maja_polaczenia]

    wg_grup = defaultdict(list)
    for dev in dev_meta:
        if dev in maja_polaczenia:
            wg_grup[grupa_dev[dev]].append(dev)

    podsum = []
    for g, devs in sorted(wg_grup.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99):
        nazwa = NAZWY_GRUP.get(g, "do_ustalenia")
        plik = f"strefa_{g}_{nazwa}.yml" if g != "0" else "strefa_0_do_ustalenia.yml"
        ark = {"connectors": {}, "cables": {}, "connections": []}

        for nr_przebiegu, dev in enumerate(devs):
            m = dev_meta[dev]
            klucz = bezpieczne(dev)
            pl = [p for _d, p, _s in dev_piny[dev]]
            lab = [s for _d, _p, s in dev_piny[dev]]
            c = {"type": esc(m["type"][:60]), "pins": pl, "pinlabels": [esc(l[:30]) for l in lab]}
            if m["subtype"]:
                c["subtype"] = esc(m["subtype"][:60])
            if m["uwagi"]:
                c["notes"] = esc(zawin(m["uwagi"]))
            ark["connectors"][klucz] = c

            moje = [x for x in polaczenia_sur if x[0] == dev]
            if not moje:
                continue
            kab = f"W_{klucz}"
            # Nazwa przebiegu zamiast samego "Kabel, N wires" - inaczej lista
            # materialowa skleja wszystkie kable o tej samej liczbie zyl w jedna
            # pozycje i nie da sie ich rozroznic.
            ark["cables"][kab] = {
                "type": f"wiazka {klucz}",
                "wirecount": len(moje),
                "colors": [zyla(k, nr_przebiegu, zk) for *_x, k, zk in moje],
                "wirelabels": [esc(str(s or p)[:24]) for _d, p, _r, _w, _pc, s, _k, _zk in moje],
                "notes": esc(uwaga_kolorow(moje)),
            }
            for i, (_d, pd, _r, wezel, pcel, _s, _k, _zk) in enumerate(moje, 1):
                cel_pin = szyna_idx[(wezel, pcel, dev)] if wezel.startswith("XB_") else pcel
                ark["connections"].append([{klucz: [pd]}, {kab: [i]}, {wezel: [cel_pin]}])

        (wyj / plik).write_text(
            naglowek + f"# STREFA {g}: {nazwa.replace('_',' ')}\n"
            + yaml.safe_dump(ark, sort_keys=False, allow_unicode=True), encoding="utf-8")
        podsum.append((plik, len(ark["connectors"]), len(ark["connections"])))

    # --- 6. raport ----------------------------------------------------------
    rap = ["RAPORT GENERACJI ARKUSZY WIREVIZ", "=" * 70, ""]
    rap.append(f"Zlacza TTC510: X1 {len(ttc['X1']['pins'])} pin., X2 {len(ttc['X2']['pins'])} pin.")
    rap.append(f"Urzadzenia: {len(dev_meta)}   Polaczen narysowanych: {len(polaczenia_sur)}")
    rap.append("")
    rap.append("LEGENDA KOLOROW ZYL:")
    for kod, opis in LEGENDA:
        rap.append(f"  {kod:3s} {opis}")
    rap.append("  (kolor z karty urzadzenia ma pierwszenstwo nad konwencja)")
    rap.append("")
    rap.append("ARKUSZE:")
    for p, nc, nconn in podsum:
        rap.append(f"  {p:42s} {nc:2d} zlacz, {nconn:3d} polaczen")
    rap.append("")
    rap.append(f"URZADZENIA BEZ ANI JEDNEGO USTALONEGO POLACZENIA ({len(bez_polaczen)}):")
    for d in bez_polaczen:
        rap.append(f"  {d:22s} {dev_meta[d]['type'][:60]}")
    rap.append("")
    rap.append(f"PINY BEZ USTALONEGO CELU - NIE NARYSOWANE ({len(raport_bez_celu)}):")
    for dev, pin, syg, powod in raport_bez_celu:
        rap.append(f"  {dev:14s} pin {str(pin):16s} {syg[:30]:30s} -> {powod[:40]}")
    tekst = "\n".join(rap)
    (wyj.parent / "RAPORT_z_csv.txt").write_text(tekst, encoding="utf-8")
    print(tekst)


if __name__ == "__main__":
    main()
