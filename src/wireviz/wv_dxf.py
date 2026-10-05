# -*- coding: utf-8 -*-
"""
Eksport wiazki do DXF (Mercedes Microdrive).

Dodane w forku silenzo85/WireViz-Microdrive. Powod: cala dokumentacja rysunkowa
projektu zyje w DXF/DWG (schemat elektryczny HY-TTC_510_Wiring_v16mod.dwg,
hydrauliczny HY-TTC_510_Hydraulika_v10.dxf) i jest sprawdzana narzedziami
_generator/audit.py oraz cross.py. Natywne wyjscia WireViz (gv/svg/png/html/tsv)
nie wchodza do tego obiegu.

Zasada dzialania:
  1. wyliczamy wlasna geometrie pudelek (naglowek + wiersz na kazdy pin / zyle),
  2. oddajemy graphviz-owi graf o TAKICH SAMYCH rozmiarach wezlow, zeby dostac
     rozmieszczenie (-Tjson) spojne z ukladem SVG,
  3. rysujemy w ezdxf wlasna geometrie na nazwanych warstwach.

Wynik jest edytowalny w CAD - user prowadzi rysunki recznie.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wireviz.wv_colors import get_color_hex, translate_color

# --- geometria rysunku (mm) -------------------------------------------------

MM_PER_POINT = 25.4 / 72.0  # graphviz podaje pozycje w punktach

ROW_H = 6.0  # wysokosc wiersza pinu / zyly
HEAD_H = 19.5  # naglowek: 1 linia tytulu + do 3 linii podtytulu
PAD = 2.0  # margines wewnetrzny

W_CONNECTOR = 78.0  # szerokosc pudelka zlacza
W_CABLE = 84.0  # szerokosc pudelka kabla
COL_PIN = 13.0  # kolumna numeru pinu / zyly
COL_SWATCH = 15.0  # kolumna probki koloru zyly

TXT_H = 2.5  # wysokosc tekstu opisowego (norma rysunkowa)
TXT_H_TITLE = 3.5  # wysokosc tekstu naglowka pudelka

# --- warstwy ----------------------------------------------------------------
# aci = kolor ACI AutoCAD; nazwy po polsku, spojnie z reszta projektu

LAYERS = {
    "WV_ZLACZE": dict(aci=5, opis="Obrys i naglowek zlacza"),
    "WV_KABEL": dict(aci=3, opis="Obrys i naglowek kabla"),
    "WV_ZYLA": dict(aci=7, opis="Zyly - kolor rzeczywisty przez true_color"),
    "WV_EKRAN": dict(aci=8, opis="Ekran kabla"),
    "WV_OPIS": dict(aci=7, opis="Opisy pinow, zyl, numeracja"),
    "WV_RAMKA": dict(aci=7, opis="Ramka i tabliczka rysunkowa"),
    "WV_LM": dict(aci=2, opis="Lista materialowa"),
}


# --- dopasowanie tekstu do szerokosci kolumny -------------------------------
# Arial: zmierzona szerokosc znaku to 0,64-0,70 wysokosci dla tekstu mieszanego
# i 0,76 dla samych cyfr (numery katalogowe!). Bierzemy 0,72 z zapasem.
# Docinamy zamiast pozwolic tekstowi
# wyjsc poza obrys - rysunek ma byc czytelny bez recznych poprawek.

CHAR_W = 0.72


def _fit(text: str, max_w: float, height: float) -> str:
    """Docina tekst do zadanej szerokosci, dokladajac wielokropek."""
    if not text:
        return ""
    text = str(text).replace("\n", " ")
    n = max(int(max_w / (height * CHAR_W)), 1)
    return text if len(text) <= n else text[: max(n - 3, 1)] + "..."


def _wrap(text: str, max_w: float, height: float, max_lines: int = 2):
    """Zawija tekst na max_lines linii; ostatnia linia docinana."""
    if not text:
        return []
    words = str(text).replace("\n", " ").split()
    n = max(int(max_w / (height * CHAR_W)), 1)
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= n:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines:
        rest = " ".join(words)
        used = " ".join(lines[:-1])
        tail = rest[len(used):].strip()
        lines[-1] = _fit(tail, max_w, height)
    return lines


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (0, 0, 0)


# --- rozmiary pudelek -------------------------------------------------------


def _connector_rows(connector) -> List[Tuple[str, str]]:
    """Zwraca wiersze zlacza: (numer pinu, etykieta)."""
    pins = list(connector.pins or [])
    labels = list(connector.pinlabels or [])
    rows = []
    for i, pin in enumerate(pins):
        label = labels[i] if i < len(labels) else ""
        rows.append((str(pin), str(label or "")))
    return rows


def _cable_rows(cable) -> List[Tuple[str, str, str]]:
    """Zwraca wiersze kabla: (numer zyly, kolor, etykieta)."""
    n = cable.wirecount or len(cable.colors) or 0
    colors = list(cable.colors or [])
    labels = list(cable.wirelabels or [])
    rows = []
    for i in range(n):
        color = colors[i] if i < len(colors) else ""
        label = labels[i] if i < len(labels) else ""
        rows.append((str(i + 1), str(color or ""), str(label or "")))
    return rows


def _box_size(n_rows: int, width: float) -> Tuple[float, float]:
    return width, HEAD_H + max(n_rows, 1) * ROW_H + PAD


# --- rozmieszczenie przez graphviz ------------------------------------------


def _layout(harness, sizes: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    """Zwraca srodki wezlow w mm, korzystajac z silnika dot."""
    import json

    from graphviz import Digraph

    g = Digraph(engine="dot")
    g.attr(rankdir="LR", nodesep="0.8", ranksep="1.6")

    for name, (w, h) in sizes.items():
        g.node(
            name,
            label="",
            shape="box",
            fixedsize="true",
            width=f"{w / 25.4:.4f}",
            height=f"{h / 25.4:.4f}",
        )

    # Kierunek krawedzi decyduje o kolumnie: zlacza zrodlowe na lewo od kabla,
    # docelowe na prawo. Bez tego dot wrzuca wszystkie zlacza w jedna kolumne.
    seen = set()
    for cable in harness.cables.values():
        for conn in cable.connections:
            if conn.from_name in sizes:
                edge = (conn.from_name, cable.name)
                if edge not in seen:
                    seen.add(edge)
                    g.edge(conn.from_name, cable.name)
            if conn.to_name in sizes:
                edge = (cable.name, conn.to_name)
                if edge not in seen:
                    seen.add(edge)
                    g.edge(cable.name, conn.to_name)

    raw = g.pipe(format="json").decode("utf-8")
    data = json.loads(raw)

    pos = {}
    for obj in data.get("objects", []):
        name = obj.get("name")
        p = obj.get("pos")
        if name and p:
            x, y = p.split(",")
            pos[name] = (float(x) * MM_PER_POINT, float(y) * MM_PER_POINT)
    return pos


# --- rysowanie --------------------------------------------------------------


ENCJE = (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"))


def _odkoduj(t):
    """Encje HTML wracaja na znaki - w DXF nie ma markupu."""
    t = str(t)
    for a, b in ENCJE:
        t = t.replace(a, b)
    return t


def _add_text(msp, text, x, y, height, layer, align_right=False):
    from ezdxf.enums import TextEntityAlignment

    text = _odkoduj(text)

    if not text:
        return
    t = msp.add_text(
        str(text).replace("\n", " "),
        height=height,
        dxfattribs={"layer": layer, "style": "Standard"},
    )
    t.set_placement(
        (x, y),
        align=TextEntityAlignment.MIDDLE_RIGHT
        if align_right
        else TextEntityAlignment.MIDDLE_LEFT,
    )


def _draw_box(msp, x, y, w, h, layer, title, subtitle):
    """Rysuje pudelko lewym-dolnym rogiem w (x, y)."""
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
        close=True,
        dxfattribs={"layer": layer},
    )
    # linia pod naglowkiem
    y_head = y + h - HEAD_H
    msp.add_line((x, y_head), (x + w, y_head), dxfattribs={"layer": layer})
    inner = w - 2 * PAD
    _add_text(msp, _fit(title, inner, TXT_H_TITLE), x + PAD, y + h - 4.5, TXT_H_TITLE, layer)
    for i, line in enumerate(_wrap(subtitle, inner, TXT_H, max_lines=3)):
        _add_text(msp, line, x + PAD, y + h - 10.0 - i * 3.6, TXT_H, "WV_OPIS")
    return y_head


def _draw_connector(msp, connector, x, y, w, h):
    rows = _connector_rows(connector)
    subtitle = " / ".join(
        [s for s in (connector.type, connector.subtype, connector.pn) if s]
    )
    y_head = _draw_box(msp, x, y, w, h, "WV_ZLACZE", connector.name, subtitle)

    row_y = {}
    for i, (pin, label) in enumerate(rows):
        cy = y_head - (i + 0.5) * ROW_H
        msp.add_line(
            (x + COL_PIN, cy - ROW_H / 2),
            (x + COL_PIN, cy + ROW_H / 2),
            dxfattribs={"layer": "WV_ZLACZE"},
        )
        _add_text(
            msp,
            _fit(pin, COL_PIN - 2 * PAD, TXT_H),
            x + COL_PIN - PAD,
            cy,
            TXT_H,
            "WV_OPIS",
            align_right=True,
        )
        _add_text(
            msp,
            _fit(label, w - COL_PIN - 2 * PAD, TXT_H),
            x + COL_PIN + PAD,
            cy,
            TXT_H,
            "WV_OPIS",
        )
        row_y[str(pin)] = cy
    return row_y


def _draw_cable(msp, cable, x, y, w, h, color_mode):
    rows = _cable_rows(cable)
    bits = []
    if cable.type:
        bits.append(str(cable.type))
    if cable.gauge:
        bits.append(f"{cable.gauge} {cable.gauge_unit or 'mm2'}")
    if cable.length:
        bits.append(f"{cable.length} {cable.length_unit or 'm'}")
    y_head = _draw_box(msp, x, y, w, h, "WV_KABEL", cable.name, " / ".join(bits))

    row_y = {}
    for i, (num, color, label) in enumerate(rows):
        cy = y_head - (i + 0.5) * ROW_H
        _add_text(msp, num, x + COL_PIN - PAD, cy, TXT_H, "WV_OPIS", align_right=True)

        # probka koloru - wypelniony prostokat w kolorze rzeczywistym
        if color:
            hexes = get_color_hex(color, pad=False)
            sw_x = x + COL_PIN + PAD
            sw_w = COL_SWATCH - 2 * PAD
            seg = sw_w / max(len(hexes), 1)
            for k, hx in enumerate(hexes):
                _solid(
                    msp,
                    sw_x + k * seg,
                    cy - 1.4,
                    seg,
                    2.8,
                    _hex_to_rgb(hx),
                    "WV_ZYLA",
                )
            _add_text(
                msp,
                translate_color(color, color_mode),
                x + COL_PIN + COL_SWATCH + PAD,
                cy,
                TXT_H,
                "WV_OPIS",
            )
        if label:
            lx = x + COL_PIN + COL_SWATCH + 14.0
            _add_text(msp, _fit(label, x + w - PAD - lx, TXT_H), lx, cy, TXT_H, "WV_OPIS")
        row_y[str(i + 1)] = cy

    if cable.shield:
        _add_text(msp, "EKRAN", x + PAD, y + PAD, TXT_H, "WV_EKRAN")
    return row_y


def _solid(msp, x, y, w, h, rgb, layer):
    import ezdxf

    msp.add_solid(
        [(x, y), (x + w, y), (x, y + h), (x + w, y + h)],
        dxfattribs={"layer": layer, "true_color": ezdxf.rgb2int(rgb)},
    )


CLR = 1.5  # luz miedzy zyla a obrysem pudelka [mm]


def _hits(x1, y1, x2, y2, rects, skip) -> bool:
    """Czy odcinek prostokatny przecina ktorekolwiek pudelko (poza skip)."""
    for name, (rx, ry, rw, rh) in rects.items():
        if name in skip:
            continue
        rx0, ry0, rx1, ry1 = rx - CLR, ry - CLR, rx + rw + CLR, ry + rh + CLR
        if abs(x1 - x2) < 1e-9:  # pionowy
            if rx0 <= x1 <= rx1 and not (max(y1, y2) < ry0 or min(y1, y2) > ry1):
                return True
        else:  # poziomy
            if ry0 <= y1 <= ry1 and not (max(x1, x2) < rx0 or min(x1, x2) > rx1):
                return True
    return False


def _channels(rects) -> List[float]:
    """Wolne pionowe korytarze miedzy kolumnami pudelek."""
    spans = sorted((r[0] - CLR, r[0] + r[2] + CLR) for r in rects.values())
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    gaps = [
        (merged[i][1] + merged[i + 1][0]) / 2.0 for i in range(len(merged) - 1)
    ]
    if merged:  # korytarze na zewnatrz skrajnych kolumn
        gaps.append(merged[0][0] - 12.0)
        gaps.append(merged[-1][1] + 12.0)
    return gaps


def _corridors(rects) -> List[float]:
    """Wolne poziome korytarze miedzy rzedami pudelek."""
    spans = sorted((r[1] - CLR, r[1] + r[3] + CLR) for r in rects.values())
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    gaps = [(merged[i][1] + merged[i + 1][0]) / 2.0 for i in range(len(merged) - 1)]
    if merged:
        gaps.append(merged[0][0] - 10.0)
        gaps.append(merged[-1][1] + 10.0)
    return gaps


def _route(p_from, p_to, rects, skip):
    """Trasa ortogonalna omijajaca pudelka. Fallback: prosto przez srodek."""
    (x1, y1), (x2, y2) = p_from, p_to
    if abs(y1 - y2) < 1e-9 and not _hits(x1, y1, x2, y2, rects, skip):
        return [(x1, y1), (x2, y2)]

    mid = (x1 + x2) / 2.0
    for cx in sorted(_channels(rects), key=lambda c: abs(c - mid)):
        if (
            not _hits(x1, y1, cx, y1, rects, skip)
            and not _hits(cx, y1, cx, y2, rects, skip)
            and not _hits(cx, y2, x2, y2, rects, skip)
        ):
            return [(x1, y1), (cx, y1), (cx, y2), (x2, y2)]

    # trasa schodkowa: dwa korytarze pionowe + jeden poziomy
    chans = sorted(_channels(rects), key=lambda c: abs(c - mid))
    ys = sorted(_corridors(rects), key=lambda v: abs(v - (y1 + y2) / 2.0))
    for c1 in chans:
        if _hits(x1, y1, c1, y1, rects, skip):
            continue
        for c2 in chans:
            if _hits(c2, y2, x2, y2, rects, skip):
                continue
            for yc in ys:
                if (
                    not _hits(c1, y1, c1, yc, rects, skip)
                    and not _hits(c1, yc, c2, yc, rects, skip)
                    and not _hits(c2, yc, c2, y2, rects, skip)
                ):
                    return [
                        (x1, y1),
                        (c1, y1),
                        (c1, yc),
                        (c2, yc),
                        (c2, y2),
                        (x2, y2),
                    ]

    # awaryjnie: obejscie gora/dolem calego rysunku
    ytop = max(r[1] + r[3] for r in rects.values()) + 10.0
    ybot = min(r[1] for r in rects.values()) - 10.0
    for yb in sorted((ytop, ybot), key=lambda v: abs(v - (y1 + y2) / 2.0)):
        stub = x1 + (6.0 if x2 > x1 else -6.0)
        if not _hits(stub, yb, x2 - (6.0 if x2 > x1 else -6.0), yb, rects, skip):
            return [
                (x1, y1),
                (stub, y1),
                (stub, yb),
                (x2 - (6.0 if x2 > x1 else -6.0), yb),
                (x2 - (6.0 if x2 > x1 else -6.0), y2),
                (x2, y2),
            ]

    return [(x1, y1), (mid, y1), (mid, y2), (x2, y2)]


def _draw_wire(msp, pts, hexes):
    """Rysuje zyle w kolorze rzeczywistym."""
    import ezdxf

    rgb = _hex_to_rgb(hexes[0]) if hexes else (0, 0, 0)
    msp.add_lwpolyline(
        pts, dxfattribs={"layer": "WV_ZYLA", "true_color": ezdxf.rgb2int(rgb)}
    )


def _draw_frame(msp, metadata, bbox, bomlist):
    """Ramka + tabliczka rysunkowa + lista materialowa pod rysunkiem."""
    x0, y0, x1, y1 = bbox
    margin = 15.0
    tb_w, tb_h = 130.0, 24.0
    row_h = 5.0
    lm_h = (len(bomlist) + 1) * row_h if bomlist else 0.0

    # LM stoi NAD tabliczka - inaczej wiersze wchodza na jej pole
    fx0, fy0 = x0 - margin, y0 - margin - tb_h - lm_h - 8.0
    fx1, fy1 = max(x1 + margin, x0 - margin + tb_w + 20.0), y1 + margin

    msp.add_lwpolyline(
        [(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)],
        close=True,
        dxfattribs={"layer": "WV_RAMKA"},
    )

    # --- tabliczka rysunkowa, prawy dolny rog ---
    tx, ty = fx1 - tb_w, fy0
    msp.add_lwpolyline(
        [(tx, ty), (tx + tb_w, ty), (tx + tb_w, ty + tb_h), (tx, ty + tb_h)],
        close=True,
        dxfattribs={"layer": "WV_RAMKA"},
    )
    msp.add_line((tx, ty + 8.0), (tx + tb_w, ty + 8.0), dxfattribs={"layer": "WV_RAMKA"})
    meta = metadata or {}
    inner = tb_w - 2 * PAD
    _add_text(
        msp, _fit(meta.get("title", "Wiazka"), inner, 4.0), tx + PAD, ty + tb_h - 6.0, 4.0, "WV_RAMKA"
    )
    line2 = " | ".join(
        [str(v) for v in (meta.get("pn"), meta.get("revision"), meta.get("date")) if v]
    )
    _add_text(msp, _fit(line2, inner, TXT_H), tx + PAD, ty + tb_h - 14.0, TXT_H, "WV_RAMKA")
    _add_text(
        msp, _fit(str(meta.get("company", "") or ""), inner, TXT_H), tx + PAD, ty + 4.0, TXT_H, "WV_RAMKA"
    )

    # --- lista materialowa, nad tabliczka, szerokosc ramki ---
    if not bomlist:
        return
    cols = [14.0, 110.0, 16.0, 16.0, 70.0, 45.0, 45.0]
    total = sum(cols[: len(bomlist[0])])
    avail = (fx1 - fx0) - 2 * PAD
    if total > avail:  # skaluj kolumny do szerokosci ramki
        k = avail / total
        cols = [c * k for c in cols]

    top = fy0 + tb_h + 8.0 + lm_h
    _add_text(msp, "LISTA MATERIALOWA", fx0 + PAD, top, TXT_H_TITLE, "WV_LM")
    for r, row in enumerate(bomlist):
        ry = top - (r + 1) * row_h
        cx = fx0 + PAD
        for c, cell in enumerate(row[: len(cols)]):
            _add_text(msp, _fit(cell, cols[c] - 2.0, TXT_H), cx, ry, TXT_H, "WV_LM")
            cx += cols[c]
        msp.add_line(
            (fx0 + PAD, ry - row_h / 2),
            (fx0 + PAD + sum(cols[: len(row)]), ry - row_h / 2),
            dxfattribs={"layer": "WV_LM"},
        )


# --- API --------------------------------------------------------------------


def export_dxf(harness, filename: str, bomlist: Optional[List[List[str]]] = None) -> None:
    """Zapisuje wiazke do <filename>.dxf."""
    try:
        import ezdxf
    except ImportError:
        raise SystemExit(
            "Eksport DXF wymaga pakietu ezdxf.  Instalacja:  pip install ezdxf"
        )

    color_mode = getattr(harness.options, "color_mode", "SHORT")

    # 1. rozmiary
    sizes = {}
    for name, c in harness.connectors.items():
        sizes[name] = _box_size(len(_connector_rows(c)), W_CONNECTOR)
    for name, c in harness.cables.items():
        sizes[name] = _box_size(len(_cable_rows(c)), W_CABLE)

    if not sizes:
        raise SystemExit("Wiazka nie zawiera zadnych elementow - nie ma czego zapisac.")

    # 2. rozmieszczenie
    pos = _layout(harness, sizes)

    # 3. rysunek
    doc = ezdxf.new("R2010", setup=True)
    for lname, spec in LAYERS.items():
        doc.layers.add(lname, color=spec["aci"])
    msp = doc.modelspace()

    origins = {}
    for name, (w, h) in sizes.items():
        cx, cy = pos.get(name, (0.0, 0.0))
        origins[name] = (cx - w / 2.0, cy - h / 2.0, w, h)

    conn_rows, cable_rows = {}, {}
    for name, c in harness.connectors.items():
        x, y, w, h = origins[name]
        conn_rows[name] = _draw_connector(msp, c, x, y, w, h)
    for name, c in harness.cables.items():
        x, y, w, h = origins[name]
        cable_rows[name] = _draw_cable(msp, c, x, y, w, h, color_mode)

    # 4. zyly
    for cname, cable in harness.cables.items():
        cx, cy, cw, ch = origins[cname]
        rows = _cable_rows(cable)
        for conn in cable.connections:
            wire = str(conn.via_port)
            if wire not in cable_rows[cname]:
                continue
            wy = cable_rows[cname][wire]
            idx = int(wire) - 1
            hexes = get_color_hex(rows[idx][1], pad=False) if idx < len(rows) else []

            for other, pin, left in (
                (conn.from_name, conn.from_pin, True),
                (conn.to_name, conn.to_pin, False),
            ):
                if not other or other not in origins or pin is None:
                    continue
                ox, oy, ow, oh = origins[other]
                py = conn_rows.get(other, {}).get(str(pin))
                if py is None:
                    continue
                # wychodzimy z tej krawedzi zlacza, ktora jest blizej kabla
                if ox < cx:
                    p_conn, p_cable = (ox + ow, py), (cx, wy)
                else:
                    p_conn, p_cable = (ox, py), (cx + cw, wy)
                pts = _route(p_conn, p_cable, origins, skip={other, cname})
                _draw_wire(msp, pts, hexes)

    # 5. ramka
    xs = [o[0] for o in origins.values()] + [o[0] + o[2] for o in origins.values()]
    ys = [o[1] for o in origins.values()] + [o[1] + o[3] for o in origins.values()]
    _draw_frame(msp, harness.metadata, (min(xs), min(ys), max(xs), max(ys)), bomlist)

    out = f"{filename}.dxf"
    doc.saveas(out)
    print(f"DXF: {out}")
