# -*- coding: utf-8 -*-
"""
kolory.py - kolory zyl dla arkuszy wiazek microdrive.

DWA ZRODLA, w tej kolejnosci:

1. KOLOR Z KARTY URZADZENIA (kolumna "Kolor zyly (karta)" w 02_urzadzenia_piny.csv).
   To jest FAKT - zyla producenta ma ten kolor. Dotyczy 28 ze 171 wierszy
   (czujniki z pigtailem: BQ3, SB2/SB3, B-SLEW).

2. KONWENCJA FUNKCYJNA - dla reszty, gdzie karta koloru NIE PODAJE.
   To jest UMOWA RYSUNKOWA, nie specyfikacja zakupowa: ma pozwolic przesledzic
   wzrokiem, co gdzie idzie. Przy zamawianiu wiazki kolory trzeba ZATWIERDZIC.
   Zyly z konwencji sa oznaczone w uwadze kabla.

CAN High = zolty, CAN Low = zielony - za SAE J1939-11 (obie nasze magistrale
to 250 kbit/s J1939/CANopen), nie z palca.
"""

import re

# --- 1. kolory z kart (polskie nazwy) -> kody WireViz ----------------------

Z_KARTY = {
    "czarny": "BK", "bialy": "WH", "biały": "WH", "szary": "GY",
    "rozowy": "PK", "różowy": "PK", "czerwony": "RD",
    "pomaranczowy": "OG", "pomarańczowy": "OG", "zolty": "YE", "żółty": "YE",
    "zielony": "GN", "niebieski": "BU", "fioletowy": "VT",
    "brazowy": "BN", "brązowy": "BN", "bezowy": "BG", "beżowy": "BG",
    "srebrny": "SR", "zloty": "GD", "złoty": "GD", "turkusowy": "TQ",
}


def z_karty(tekst):
    """'brazowy (typowo)' -> 'BN'. Zwraca None, gdy karta nic nie podaje."""
    t = (tekst or "").strip().lower()
    if not t:
        return None
    for nazwa, kod in Z_KARTY.items():
        if nazwa in t:
            return kod
    return None


# --- 2. konwencja funkcyjna ------------------------------------------------
# Kolejnosc MA ZNACZENIE - pierwsza pasujaca regula wygrywa.
# Uwaga: "Signal + (zasilanie petli)" musi trafic na ZASILANIE, a
# "Signal - (wyjscie pradowe)" na SYGNAL ANALOGOWY - stad zasilanie przed sygnalem.

LEGENDA = [
    ("RD", "zasilanie (+24 V, +5 V, Clamp 30, BAT+)"),
    ("BK", "masa (GND, 0 V, BAT-, SGND)"),
    ("YE", "CAN High (J1939-11)"),
    ("GN", "CAN Low (J1939-11)"),
    ("GY", "ekran / nieokreslone"),
    ("BU", "sygnal analogowy (4..20 mA, 0,5..4,5 V)"),
    ("WH", "sygnal cyfrowy / styk / czujnik impulsowy"),
    ("BN", "wyjscie mocy - cewka, przekaznik, beacon, buzzer"),
    ("PK", "powrot cewki przez wyjscie LS (drugi tor odciecia)"),
    ("VT", "wideo CVBS"),
]

_REGULY = [
    # ekran / wideo
    (r"ekran|shield|shld|oplot", "GY"),
    (r"video.*sygnal|video rg|wideo", "VT"),
    (r"video.*gnd|camera\d* gnd", "BK"),
    # magistrale
    (r"can[_ ]?gnd|can gnd", "BK"),
    (r"can[_ ]?v\+", "RD"),
    (r"can.*\b(h|high)\b|can\d*[_ ]?h\b", "YE"),
    (r"can.*\b(l|low)\b|can\d*[_ ]?l\b", "GN"),
    (r"^can\b|^can ", "YE"),
    # wyjscia mocy i ich powroty
    (r"cewka.*-\s*$|powrot cewki|out\d-", "COIL_RET"),
    (r"cewka|lapa \d (wysuw|wsuw)|silownik hamulca|beacon|buzzer|out\d\+"
     r"|zasilanie wentylatora|rownolegle do wlacznika", "BN"),
    # masy
    (r"\bmasa\b|\bgnd\b|\bground\b|\b0 ?v\b|\bbat-|logic_gnd|sgnd", "BK"),
    # zasilania
    (r"zasilanie|\+5 ?v|\+24|\+8|\+v|clamp 30|\bbat\+|supply|vsupply|power \d"
     r"|rtc supply|terminal 15|wake.?up|service enable|spare|\baux\b", "RD"),
    # sygnaly analogowe
    (r"wyjscie pradowe|signal\s*-|0,5\.\.4,5|\bain\b|in_ref|output|potencjometr", "BU"),
    # sygnaly cyfrowe / styki
    (r"styk|\bnc\d?\b|\bno\d?\b|sygnal|deadman|in[1-4]\b|sig_out|rs-232|lin\b", "WH"),
]
_SKOMPILOWANE = [(re.compile(w, re.I), k) for w, k in _REGULY]


def z_funkcji(sygnal, cel_to_pin_ttc=False):
    """
    Kolor z konwencji funkcyjnej. `cel_to_pin_ttc` rozroznia powrot cewki
    na wyjscie LS sterownika (PK - drugi tor odciecia, np. S1/S2 przez P251)
    od zwyklego powrotu na szyne 0 V (BK).
    """
    s = (sygnal or "").strip()
    for wzor, kod in _SKOMPILOWANE:
        if wzor.search(s):
            if kod == "COIL_RET":
                return "PK" if cel_to_pin_ttc else "BK"
            return kod
    return "GY"


def kolor(sygnal, kolor_karty, cel_to_pin_ttc=False):
    """Zwraca (kod, czy_z_karty)."""
    k = z_karty(kolor_karty)
    if k:
        return k, True
    return z_funkcji(sygnal, cel_to_pin_ttc), False


# --- pasek rozrozniajacy PRZEBIEG -----------------------------------------
# Sama funkcja daje 3-4 kolory na arkusz: osiem cewek YV to osiem identycznych
# brazowych zyl i nie widac, ktora gdzie idzie. Dlatego zyla = BAZA (funkcja)
# + PASEK (numer przebiegu), jak w wiazkach samochodowych.
# Zyly, ktorych kolor pochodzi z KARTY urzadzenia, zostaja jednolite - to fakt,
# nie wolno go zasmiecac paskiem.

PASKI = ["WH", "GN", "YE", "BU", "VT", "OG", "PK", "RD", "TQ", "BG",
         "GY", "BK", "BN", "LB", "SL", "IV"]


def pasek(nr):
    """Kolor paska dla n-tego przebiegu na arkuszu."""
    return PASKI[nr % len(PASKI)]


def zyla(baza, nr_przebiegu, z_karty_flaga):
    """
    Zwraca kod koloru zyly dla WireViz.
    Jednolity, gdy kolor jest z karty; inaczej 'BAZA+PASEK' (zyla w paski).
    """
    if z_karty_flaga:
        return baza
    p = pasek(nr_przebiegu)
    return baza if p == baza else baza + p
