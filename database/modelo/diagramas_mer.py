# Chen-notation TikZ diagrams of the integrated MER, one per module.
# Called from modelo_bna.py; layouts (entity coordinates in cm) live here.
import math
import os

from modelo_bna import E, R, esc

RID = {r["id"]: r for r in R}

# ---------------------------------------------------------------------------
# Layouts.  own: entities drawn with attributes; other positioned entities are
# drawn as references (grey, no attributes).  dia: diamond position overrides.
# ---------------------------------------------------------------------------
DIAGRAMS = [
    dict(key="core", caption="Núcleo contable (CORE) y auditoría transversal",
         own=["ASIENTO_CONTABLE", "DETALLE_ASIENTO", "CUENTA_CONTABLE", "AGENCIA", "EVENTO_AUDITORIA"],
         pos={"ASIENTO_CONTABLE": (-3.5, 6.5), "DETALLE_ASIENTO": (-3.5, 0.5),
              "CUENTA_CONTABLE": (4, 0.5), "AGENCIA": (-4, -4.5), "EVENTO_AUDITORIA": (4, -5)},
         rels=["R01", "R02", "R03", "R04"],
         dia={"R04": (2.2, 4.2), "R03": (4, 4.2)}),
    dict(key="cli", caption="Clientes (KYC / biometría)",
         own=["CLIENTE", "BIOMETRIA_CLIENTE", "CODIGO_VERIFICACION", "VALIDACION_IDENTIDAD"],
         pos={"CLIENTE": (0, 2.5), "BIOMETRIA_CLIENTE": (-5.5, -5.5),
              "CODIGO_VERIFICACION": (0, -7.5), "VALIDACION_IDENTIDAD": (5.5, -5.5)},
         rels=["R07", "R08", "R09"]),
    dict(key="cta", caption="Cuentas de ahorro",
         own=["CUENTA_AHORRO", "MOVIMIENTO", "CONSUMO_DIARIO"],
         pos={"CUENTA_AHORRO": (-3, 3), "CLIENTE": (-3, 9.5), "AGENCIA": (4.5, 7.5),
              "MOVIMIENTO": (4, -1.5), "ASIENTO_CONTABLE": (4, -9), "CANAL": (-3, -8.5),
              "CONSUMO_DIARIO": (-6, -2.5)},
         rels=["R05", "R06", "R10", "R11", "R12", "R13", "R14"]),
    dict(key="tar1", caption="Tarjetas: tarjeta, credenciales y tokens",
         own=["TARJETA", "CREDENCIAL", "MATRIZ_TOKEN", "MATRIZ_COORDENADA", "TOKEN_PAGO"],
         pos={"TARJETA": (0, 2), "CLIENTE": (-5, 9), "CUENTA_AHORRO": (5, 9),
              "CREDENCIAL": (-6, -3), "TOKEN_PAGO": (6, -3),
              "MATRIZ_TOKEN": (0, -6.5), "MATRIZ_COORDENADA": (0, -11.5)},
         rels=["R16", "R17", "R18", "R19", "R20", "R21"]),
    dict(key="tar2", caption="Tarjetas: canales, autorizaciones y bitácoras",
         own=["CANAL", "LIMITE_CANAL", "INTENTO_AUTENTICACION", "AUTORIZACION",
              "HISTORIAL_ESTADO_TARJETA", "EVENTO_SALIDA"],
         pos={"TARJETA": (0, 8.5), "HISTORIAL_ESTADO_TARJETA": (-5.5, 6), "EVENTO_SALIDA": (5.5, 6),
              "INTENTO_AUTENTICACION": (-4.5, -0.5), "AUTORIZACION": (4.5, 0),
              "CANAL": (0, -6), "LIMITE_CANAL": (-5, -10), "CUENTA_AHORRO": (7, -5),
              "MOVIMIENTO": (5, -10)},
         rels=["R15", "R22", "R23", "R24", "R25", "R26", "R27", "R28", "R29"]),
    dict(key="sol", caption="Solicitud de crédito",
         own=["SOLICITUD_CREDITO", "HISTORIAL_ESTADO_SOLICITUD", "GARANTIA", "FIADOR",
              "CALENDARIO_PAGO", "CUOTA"],
         pos={"SOLICITUD_CREDITO": (0, 3), "CLIENTE": (-5, 9), "FIADOR": (5, 8.5),
              "HISTORIAL_ESTADO_SOLICITUD": (-5.5, -1.5), "GARANTIA": (5.5, -1.5),
              "CALENDARIO_PAGO": (0, -4), "CUOTA": (0, -9.5)},
         rels=["R30", "R31", "R32", "R33", "R34", "R35"]),
    dict(key="eva", caption="Evaluación crediticia",
         own=["SITUACION_FINANCIERA", "EVALUACION", "REGLA_EVALUACION", "ANALISTA", "DECISION_ANALISTA"],
         pos={"EVALUACION": (0, 1), "SOLICITUD_CREDITO": (0, 9.5), "SITUACION_FINANCIERA": (-5.5, 5.5),
              "CLIENTE": (-5.5, 10.5), "REGLA_EVALUACION": (5.5, 5.5),
              "DECISION_ANALISTA": (-4.5, -7), "ANALISTA": (4.5, -7)},
         rels=["R36", "R37", "R38", "R39", "R40", "R41", "R42"]),
    dict(key="des1", caption="Desembolso: orden y registros dependientes",
         own=["ORDEN_DESEMBOLSO", "VALIDACION_DESEMBOLSO", "EVENTO_ENTREGA", "SOLICITUD_REVERSION"],
         pos={"ORDEN_DESEMBOLSO": (0, 3.5), "VALIDACION_DESEMBOLSO": (-5.5, -4),
              "EVENTO_ENTREGA": (5.5, -4), "SOLICITUD_REVERSION": (0, -7), "MOVIMIENTO": (5, -10.5)},
         rels=["R49", "R50", "R51", "R52", "R53"],
         dia={"R52": (6.5, 0.5)}),
    dict(key="des2", caption="Desembolso: referencias de la orden a otros módulos",
         own=[],
         pos={"ORDEN_DESEMBOLSO": (0, 0), "EVALUACION": (-5, 6), "SOLICITUD_CREDITO": (0, 7),
              "CLIENTE": (5, 6), "CUENTA_AHORRO": (-5, -6), "CANAL": (0, -7), "AGENCIA": (5, -6)},
         rels=["R43", "R44", "R45", "R46", "R47", "R48"]),
    dict(key="cob", caption="Cobranza",
         own=["CREDITO", "PAGO", "MORA"],
         pos={"CREDITO": (0, 4), "ORDEN_DESEMBOLSO": (-5, 9.5), "CLIENTE": (5, 9.5),
              "CALENDARIO_PAGO": (-6, 1), "PAGO": (4.5, -2.5), "CANAL": (6.5, -8.5),
              "CUOTA": (-3, -5.5), "MORA": (-3, -10.5)},
         rels=["R54", "R55", "R56", "R57", "R58", "R59", "R60"],
         dia={"R59": (1, -4)}),
]

# ---------------------------------------------------------------------------
# Geometry helpers (sizes in cm, estimated from the fonts used below)
# ---------------------------------------------------------------------------
CW_ATTR = 0.093   # \tiny\ttfamily character width
CW_ENT = 0.13     # \scriptsize\ttfamily
CW_REL = 0.093


def attr_size(name):
    return ((CW_ATTR * len(name) + 0.06) * 1.42 + 0.05, 0.6)


def ent_size(name):
    return (CW_ENT * len(name) + 0.45, 0.62)


def rel_size(name):
    w = CW_REL * len(name) * 1.55 + 0.5
    return (w, w / 3.0 + 0.25)


def overlap(a, b, pad=0.12):
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    dx = (aw + bw) / 2 + pad - abs(ax - bx)
    dy = (ah + bh) / 2 + pad - abs(ay - by)
    return dx, dy


def layout(d):
    pos = dict(d["pos"])
    boxes_fixed = {}
    for n, (x, y) in pos.items():
        w, h = ent_size(n)
        boxes_fixed["E:" + n] = [x, y, w, h]
    diam = {}
    for rid in d["rels"]:
        r = RID[rid]
        if rid in d.get("dia", {}):
            x, y = d["dia"][rid]
        elif r["e1"] == r["e2"]:
            x, y = pos[r["e1"]][0] + 4, pos[r["e1"]][1]
        else:
            (x1, y1), (x2, y2) = pos[r["e1"]], pos[r["e2"]]
            x, y = (x1 + x2) / 2, (y1 + y2) / 2
        diam[rid] = (x, y)
        w, h = rel_size(r["name"])
        boxes_fixed["R:" + rid] = [x, y, w, h]

    # anchors for attributes: entity attributes and relationship attributes
    movable = {}   # key -> [x, y, w, h, tx, ty, parent_key]

    def place(parent_key, cx, cy, pw, ph, items, used_angles):
        if not items:
            return
        N = 144
        used = [u % (2 * math.pi) for u in used_angles]
        gap = math.radians(22)
        free = []
        for i in range(N):
            t = i * 2 * math.pi / N
            dist = min([abs((t - u + math.pi) % (2 * math.pi) - math.pi) for u in used] or [math.pi])
            if dist > gap:
                aw = max(it[1] for it in items)
                tx = cx + (pw / 2 + aw / 2 + 0.5) * math.cos(t)
                ty = cy + (ph / 2 + 0.8) * math.sin(t)
                if not hits(tx, ty, aw * 0.8, 0.46):
                    free.append(t)
        free = free or [i * 2 * math.pi / N for i in range(N)]
        # rotate so the free list starts right after a used line (contiguous)
        if used and len(free) < N:
            k = next(i for i in range(len(free)) if
                     (free[i] - free[i - 1]) % (2 * math.pi) > 2 * math.pi / N + 1e-6)
            free = free[k:] + free[:k]
        weights = [1 + 0.8 * len(it[3]) for it in items]
        total = sum(weights)
        acc = 0.0
        nf = len(free)
        for i, (key, w, h, comps) in enumerate(items):
            lo = free[int(acc / total * nf) % nf]
            mid = free[int((acc + weights[i] / 2) / total * nf) % nf]
            acc += weights[i]
            t = mid
            nr = 3 if len(items) > 9 else (2 if len(items) > 5 else 1)
            alt = 0.75 * (i % nr)
            rx = pw / 2 + w / 2 + 0.5 + alt
            ry = ph / 2 + 0.8 + alt * 0.8
            x, y = cx + rx * math.cos(t), cy + ry * math.sin(t)
            movable[key] = [x, y, w, h, x, y, parent_key]
            nc = len(comps)
            for j, (ckey, cw, ch) in enumerate(comps):
                # components: one step further out, stacked across the radius
                off = j - (nc - 1) / 2
                ux, uy = math.cos(t), math.sin(t)
                px, py = -uy, ux
                dist_out = w / 2 + cw / 2 + 0.25 if abs(ux) > 0.6 else 0.95
                cxx = x + ux * dist_out + px * off * (0.55 if abs(ux) > 0.6 else cw * 0.0 + 1.0)
                cyy = y + uy * dist_out + py * off * (0.55 if abs(ux) > 0.6 else 0.0)
                if abs(ux) <= 0.6:
                    cxx = x + off * (max(cw, 1.2) + 0.15)
                    cyy = y + uy * 0.95
                movable[ckey] = [cxx, cyy, cw, ch, cxx, cyy, key]

    segs = []
    for rid, (x, y) in diam.items():
        r = RID[rid]
        for e in {r["e1"], r["e2"]}:
            segs.append((pos[e][0], pos[e][1], x, y))

    def hits(x, y, w, h):
        for (x1, y1, x2, y2) in segs:
            for i in range(31):
                t = i / 30
                px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                if abs(px - x) < w / 2 + 0.1 and abs(py - y) < h / 2 + 0.1:
                    return True
        return False

    lines_at = {n: [] for n in pos}
    for rid, (x, y) in diam.items():
        r = RID[rid]
        for e in {r["e1"], r["e2"]}:
            ex, ey = pos[e]
            if r["e1"] == r["e2"]:
                a = math.atan2(y - ey, x - ex)
                lines_at[e] += [a - 0.35, a + 0.35]
            else:
                lines_at[e].append(math.atan2(y - ey, x - ex))

    for n in d["own"]:
        ex, ey = pos[n]
        ew, eh = ent_size(n)
        items = []
        for a in sorted(E[n]["attrs"], key=lambda z: z["key"] not in ("PK", "PP")):
            w, h = attr_size(a["name"])
            comps = [("A:%s:%s:%s" % (n, a["name"], c), *attr_size(c)) for c, _ in (a["comp"] or [])]
            items.append(("A:%s:%s" % (n, a["name"]), w, h, comps))
        place("E:" + n, ex, ey, ew, eh, items, lines_at[n])

    for rid, (x, y) in diam.items():
        r = RID[rid]
        if not r["attrs"]:
            continue
        w, h = rel_size(r["name"])
        used = [math.atan2(pos[e][1] - y, pos[e][0] - x) for e in (r["e1"], r["e2"])]
        items = [("RA:%s:%s" % (rid, a), *attr_size(a), []) for a in r["attrs"]]
        place("R:" + rid, x, y, w, h, items, used)

    # relationship lines act as obstacles (sampled points along each line)
    for rid, (x, y) in diam.items():
        r = RID[rid]
        if r["e1"] == r["e2"]:
            continue
        for e in (r["e1"], r["e2"]):
            ex, ey = pos[e]
            L = math.hypot(x - ex, y - ey)
            k = int(L / 0.2)
            for i in range(1, k):
                t = i / k
                boxes_fixed["L:%s:%s:%d" % (rid, e, i)] = [ex + (x - ex) * t, ey + (y - ey) * t, 0.08, 0.08,
                                                          -(y - ey) / L, (x - ex) / L]

    # relaxation: push movable boxes apart, spring back to target
    keys = list(movable)
    for it in range(400):
        for i, k in enumerate(keys):
            a = movable[k]
            spring = 0.03 if it < 300 else 0.0
            fx = (a[4] - a[0]) * spring
            fy = (a[5] - a[1]) * spring
            for k2 in keys[i + 1:]:
                b = movable[k2]
                dx, dy = overlap(a[:4], b[:4])
                if dx > 0 and dy > 0:
                    if dx < dy * 2.2:
                        s = 0.5 * dx * (1 if a[0] >= b[0] else -1)
                        a[0] += s
                        b[0] -= s
                    else:
                        s = 0.5 * dy * (1 if a[1] >= b[1] else -1)
                        a[1] += s
                        b[1] -= s
            for fb in boxes_fixed.values():
                dx, dy = overlap(a[:4], fb[:4], pad=0.18 if len(fb) == 4 else 0.12)
                if dx > 0 and dy > 0 and len(fb) == 6:
                    nx, ny = fb[4], fb[5]
                    side = 1 if (a[0] - fb[0]) * nx + (a[1] - fb[1]) * ny >= 0 else -1
                    step = min(dx / max(abs(nx), 1e-3), dy / max(abs(ny), 1e-3)) * 0.5 + 0.02
                    a[0] += side * nx * step
                    a[1] += side * ny * step
                elif dx > 0 and dy > 0:
                    if dx < dy * 2.2:
                        a[0] += dx * (1 if a[0] >= fb[0] else -1)
                    else:
                        a[1] += dy * (1 if a[1] >= fb[1] else -1)
            a[0] += fx
            a[1] += fy
    return pos, diam, movable


# ---------------------------------------------------------------------------
# TikZ output
# ---------------------------------------------------------------------------
def nid(s):
    return s.replace(":", "-").replace("_", "")


def tikz(d):
    pos, diam, mov = layout(d)
    L = [r"\begin{tikzpicture}[mer]"]
    for n, (x, y) in pos.items():
        style = "ent" if n in d["own"] else "entref"
        if E[n]["kind"] == "débil":
            style += ",weak"
        L.append(r"\node[%s] (%s) at (%.2f,%.2f) {%s};" % (style, nid("E:" + n), x, y, esc(n)))
    for rid, (x, y) in diam.items():
        r = RID[rid]
        style = "rel" + (",ident" if r["ident"] else "")
        L.append(r"\node[%s] (%s) at (%.2f,%.2f) {%s};" % (style, nid("R:" + rid), x, y, esc(r["name"])))
    # attributes
    for k, (x, y, w, h, _, _, parent) in mov.items():
        parts = k.split(":")
        if parts[0] == "RA":
            label, a = parts[2], None
        else:
            n, an = parts[1], parts[2]
            a = next(z for z in E[n]["attrs"] if z["name"] == an)
            label = parts[3] if len(parts) == 4 else an
            if len(parts) == 4:
                a = None
        style = "att"
        text = esc(label)
        if a:
            if a["mv"]:
                style += ",multi"
            if a["der"]:
                style += ",derived"
            if a["key"] in ("PK", "UK"):
                text = r"\underline{%s}" % text
            elif a["key"] == "PP":
                text = r"\partialkey{%s}" % text
        L.append(r"\node[%s] (%s) at (%.2f,%.2f) {%s};" % (style, nid(k), x, y, text))
        L.append(r"\draw[attline] (%s) -- (%s);" % (nid(parent), nid(k)))
    # relationship lines
    for rid in d["rels"]:
        r = RID[rid]
        c1, c2 = r["card"].split(":")
        dn = nid("R:" + rid)
        for e, card, part, bend, role in (
                (r["e1"], c1, r["p1"], 25, r["roles"][0] if r["roles"] else ""),
                (r["e2"], c2, r["p2"], -25, r["roles"][1] if r["roles"] else "")):
            en = nid("E:" + e)
            style = "total" if part == "T" else "partial"
            lab = card + (r" \textit{(%s)}" % role if role else "")
            if r["e1"] == r["e2"]:
                L.append(r"\draw[%s] (%s) to[bend left=%d] node[card,pos=0.22] {%s} (%s);" % (style, en, bend, lab, dn))
            else:
                L.append(r"\draw[%s] (%s) -- node[card,pos=0.2] {%s} (%s);" % (style, en, lab, dn))
    L.append(r"\end{tikzpicture}")
    return "\n".join(L) + "\n"


def gen(out):
    hdr = "% Generated by diagramas_mer.py -- Chen notation, do not edit by hand.\n"
    for d in DIAGRAMS:
        with open(os.path.join(out, "mer-diagrama-%s.tex" % d["key"]), "w", encoding="utf-8") as f:
            f.write(hdr + tikz(d))
    figs = [hdr]
    for d in DIAGRAMS:
        refs = sorted({n for n in d["pos"] if n not in d["own"]})
        note = "Elaboración propia. "
        if not d["own"]:
            note += ("Todas las entidades se muestran sin atributos; los de "
                     "\\texttt{ORDEN\\_DESEMBOLSO} figuran en el diagrama anterior.")
        elif refs:
            note += ("Las entidades sombreadas y de borde discontinuo pertenecen a otro "
                     "módulo y se muestran sin atributos: %s." % ", ".join(r"\texttt{%s}" % esc(n) for n in refs))
        figs.append("\n".join([
            r"\begin{figure}[H]",
            r"  \caption{Modelo entidad--relación: %s}\label{fig:mer-%s}" % (d["caption"], d["key"]),
            r"  {\centering",
            r"  \adjustbox{max width=\linewidth, max totalheight=0.78\textheight}{%",
            r"    \input{\ModelDir/mer-diagrama-%s.tex}}\par}" % d["key"],
            r"  \figurenote{%s}" % note,
            r"\end{figure}", ""]))
    with open(os.path.join(out, "mer-figuras.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(figs))
    # check coverage: every entity and relationship drawn with attributes once
    owned = [n for d in DIAGRAMS for n in d["own"]]
    rels = [r for d in DIAGRAMS for r in d["rels"]]
    miss_e = [n for n in E if n not in owned and n != "ORDEN_DESEMBOLSO"]
    miss_r = [r["id"] for r in R if r["id"] not in rels]
    if miss_e or miss_r or len(rels) != len(set(rels)):
        print("DIAGRAM COVERAGE:", miss_e, miss_r)
