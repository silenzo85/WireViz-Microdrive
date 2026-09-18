# WireViz — fork projektu Mercedes Microdrive

Fork `wireviz/WireViz` (GPLv3) przystosowany do rysowania wiązek zabudowy
microdrive na Mercedesie AROCS, sterowanej przez HY-TTC 510.

Upstream: https://github.com/wireviz/WireViz (v0.4.1, `master`)
Fork: https://github.com/silenzo85/WireViz-Microdrive, gałąź `microdrive`

---

## Co zostało zmienione względem upstreamu

| Zmiana | Pliki | Po co |
|---|---|---|
| **Eksport DXF** (format `d`) | `src/wireviz/wv_dxf.py` (nowy), `Harness.py`, `wv_cli.py` | Cała dokumentacja rysunkowa projektu żyje w DXF/DWG i jest sprawdzana przez `schematy/_generator/audit.py`. Natywne wyjścia WireViz (gv/svg/png/html/tsv) do tego obiegu nie wchodzą. |
| **Polskie skróty kolorów żył** — tryby `POL` i `POLFULL` | `src/wireviz/wv_colors.py` | Dokumentacja projektu jest po polsku. Bez znaków diakrytycznych, bo tekst trafia do DXF. |
| **Polskie nagłówki listy materiałowej** | `src/wireviz/wv_bom.py` | j.w. Wyłącznik: `WIREVIZ_LANG=en` przywraca oryginał. |
| **Scalanie arkuszy strefowych** | `microdrive/zloz.py` (narzędzie, poza pakietem) | natywne `-p/--prepend` w WireViz składa pliki **jako tekst** — powtórzona sekcja `connectors:` nadpisuje poprzednią **bez ostrzeżenia**. Sprawdzone: sklejenie dwóch plików po 1 złączu daje 1 złącze. |
| **`ezdxf` jako zależność** | `requirements.txt`, `setup.py` | potrzebny do eksportu DXF |

Nic poza tym nie ruszane — merge ze zmianami upstreamu pozostaje możliwy.

## Struktura DXF

Rysunek trafia na nazwane warstwy, żeby dało się nim sterować w CAD:

| Warstwa | Zawartość |
|---|---|
| `WV_ZLACZE` | obrysy i nagłówki złączy |
| `WV_KABEL` | obrysy i nagłówki kabli |
| `WV_ZYLA` | żyły + próbki koloru (kolor rzeczywisty przez `true_color`) |
| `WV_EKRAN` | oznaczenie ekranu |
| `WV_OPIS` | opisy pinów, żył, numeracja |
| `WV_RAMKA` | ramka i tabliczka rysunkowa |
| `WV_LM` | lista materiałowa |

Jednostki: **milimetry**. Wysokość tekstu opisowego 2,5 mm, nagłówków 3,5 mm.

Rozmieszczenie liczy silnik `dot` — dostaje graf o **takich samych rozmiarach węzłów**
jak nasze pudełka w DXF, więc układ zgadza się z tym, co widać w SVG. Kierunek
krawędzi (złącze źródłowe → kabel → złącze docelowe) wymusza kolumny.

## Użycie

```powershell
.\microdrive\wireviz.ps1 microdrive\W_czujniki_cisnienia.yml
```

Launcher sam doklei Graphviz do `PATH` na czas wywołania (binarka jest
w `C:\Program Files\Graphviz\bin`, ale nie ma jej w PATH systemowym) i dołączy
`_szablon.yml`. Wynik ląduje w `rysunki\`.

Formaty: `d` DXF · `h` HTML · `p` PNG · `s` SVG · `g` GV · `t` TSV (lista materiałowa).

Bez launchera:

```powershell
wireviz -p microdrive\_szablon.yml microdrive\W_czujniki_cisnienia.yml -f dhpst -o rysunki
```

## Pliki

- `_szablon.yml` — wspólne konwencje (kolory po polsku, dane firmy). Dołączany do każdej wiązki przez `-p`.
- `W_czujniki_cisnienia.yml` — wiązka BP1…BP6 → HY-TTC 510. Pierwsza wiązka projektu, zarazem test uruchomieniowy.

## Pułapki

- **Nie używać klucza `name:`** w definicji złącza ani kabla — WireViz sam podstawia oznaczenie i wywala się na `got multiple values for keyword argument 'name'`.
- Kotwice YAML (`&hpt` / `*hpt`) działają i są właściwym sposobem na powtarzalne elementy (6 identycznych czujników).
- Tekst jest **docinany do szerokości pudełka** (przyjęta szerokość znaku 0,72 × wysokość — zmierzona dla Arial: 0,64–0,70 dla tekstu mieszanego, 0,76 dla samych cyfr). Jeśli numer katalogowy się urywa, poszerz `W_CONNECTOR` / `W_CABLE` w `wv_dxf.py`.
- Instalacja edytowalna (`pip install -e .`) — zmiany w `src/wireviz/` działają od razu, bez przeinstalowania.

## Licencja

Upstream jest na **GPLv3** i fork to dziedziczy. Dopóki narzędzie jest używane
wewnętrznie (generujemy rysunek, klientowi idzie DXF/PDF), nie ma obowiązku
publikowania czegokolwiek — same wygenerowane rysunki nie są objęte GPL.
Obowiązek udostępnienia źródeł pojawia się dopiero, gdyby **zmodyfikowane
narzędzie** trafiło do odbiorcy.
