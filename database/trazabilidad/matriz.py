# Genera la matriz de trazabilidad de la versión MySQL (rama mysql) a partir
# del catálogo de fuentes (catalogo.py), de las fallas de la línea base MySQL
# (referencias_mysql.csv), de las salidas de las pruebas en MySQL
# (resultados/mysql/) y de las de PostgreSQL en la rama main (MAIN_COMMIT,
# leídas con git show):
#   resultados/trazabilidad.csv y .md     matriz completa
#   resultados/referencias_mysql.md       cada falla con su línea en ab6a6ec
#   informe/mysql-trazabilidad.tex        filas del anexo de la versión MySQL
#   informe/mysql-reglas.tex              cómo se cumple cada regla en cada gestor
#   informe/mysql-comparacion.tex         resultado de cada prueba en cada gestor
#   informe/mysql-brechas.tex             brechas conocidas de MySQL
#   informe/mysql-stats.tex               cifras para el texto (\statmy)
# Se detiene si una prueba no tiene fuente, si una línea citada de ab6a6ec no
# contiene el fragmento registrado, si falta en MySQL una prueba de main, si
# una prueba de MySQL falla o una brecha deja de confirmarse, o si el modelo
# (fragmentos del informe y sus generadores) difiere del de main.
# Uso: python3 trazabilidad/matriz.py
import csv
import datetime
import io
import os
import re
import subprocess
import sys
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import catalogo  # noqa: E402

RES = os.path.join(ROOT, "resultados")
INF = os.path.join(ROOT, "informe")
BASE = "ab6a6ec"
PREFIJO = "backend/Trabajo_hecho/"
MAIN = catalogo.MAIN_COMMIT
SOLO_MYSQL = {"L02", "M20c", "F32", "G01", "G02", "G03", "G04", "G05"}
# Archivos del modelo que deben ser idénticos en las dos ramas.
MODELO = re.compile(r"^(modelo/(modelo_bna|diagramas_mer)\.py|informe/(rel-macros|mer-.*|paso\d|mr-resultante|"
                    r"catalogos|esquema-final|verificacion-final)\.tex)$")

DOCS = {"BNA2026Clientes": "Clientes", "BNA2026Cuentas": "Cuentas", "BNA2026Tarjetas": "Tarjetas",
        "BNA2026Solicitud": "Solicitud", "BNA2026Evaluacion": "Evaluación",
        "BNA2026Desembolso": "Desembolso", "BNA2026Cobranza": "Cobranza", "BNA2026Core": "CORE",
        "BNA2026Stack": "Tecnologías", "MySQL2024Manual": "Manual de MySQL 8.4",
        "PostgreSQL2023Docs": "Documentación de PostgreSQL 16"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
CATEGORIA = {"pasa": "Pasa", "pasa vía privilegio": "Pasa (privilegio)",
             "pasa vía procedimiento": "Pasa (procedimiento)",
             "pasa vía procedimiento y privilegio": "Pasa (procedimiento y privilegio)",
             "brecha conocida": "Brecha conocida", "N/A": "N/A", "falla": "Falla"}
ABREV = {"pasa": "P", "pasa vía privilegio": "P\\textsubscript{v}", "pasa vía procedimiento": "P\\textsubscript{p}",
         "pasa vía procedimiento y privilegio": "P\\textsubscript{pv}", "brecha conocida": "B", "N/A": "N/A",
         "falla": "F", "—": "—"}


def falla(msg):
    sys.exit("matriz.py: " + msg)


def git(*args):
    return subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True, check=True).stdout


def leer_csv(*partes):
    with open(os.path.join(RES, *partes), newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def metadatos_de(texto):
    d = {}
    for linea in texto.splitlines():
        k, _, v = linea.partition(": ")
        d[k] = v.strip()
    return d


def fecha_larga(iso):
    t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(zoneinfo.ZoneInfo("America/Lima"))
    return "%d de %s de %d" % (t.day, MESES[t.month - 1], t.year)


# --- LaTeX -------------------------------------------------------------------
TEX = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#",
       "$": r"\$", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
       # «"» es un atajo de babel en español y se come el espacio siguiente.
       '"': r"\textquotedbl{}"}


def binario_legible(s):
    """MySQL escribe una clave binaria duplicada como '\\xE0\\x00...@...'; si son
    16 bytes, se muestra como UUID."""
    def uuid(m):
        partes = re.findall(r"\\x([0-9A-Fa-f]{2})|(.)", m.group(1), flags=re.S)
        datos = bytes(int(h, 16) if h else ord(c) for h, c in partes)
        if len(datos) != 16:
            return m.group(0)
        h = datos.hex()
        return "'%s-%s-%s-%s-%s'" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])
    return re.sub(r"'((?:\\x[0-9A-Fa-f]{2}|[^'\\])*\\x[0-9A-Fa-f]{2}(?:\\x[0-9A-Fa-f]{2}|[^'\\])*)'", uuid, s)


def tex(s):
    s = "".join(TEX.get(c, c) for c in binario_legible(s))
    return re.sub(r"(?<![\w\\/.])([\w/.]*\w(?:\\_\w+)+(?:\.\w+)?(?:\(\))?)",
                  lambda m: r"\nm{%s}" % m.group(1).replace(".", r".\allowbreak "), s)


def nm(s):
    """Ruta en mecanográfica, con cortes posibles tras «/» y «_»."""
    return r"\nm{%s}" % s.replace("_", r"\_").replace("/", r"/\allowbreak ").replace(":", r"\allowbreak :")


def cita(fuentes):
    """\\parencite de una lista de (clave, localizador)."""
    if not fuentes:
        return ""
    if len(fuentes) == 1:
        k, loc = fuentes[0]
        return r"\parencite[%s]{%s}" % (loc, k) if loc else r"\parencite{%s}" % k
    return r"\parencites" + "".join(("[%s]{%s}" % (loc, k)) if loc else "{%s}" % k for k, loc in fuentes)


def texto_fuente(fuentes):
    return "; ".join(DOCS.get(k, k) + (" " + loc.replace("~", " ") if loc else "") for k, loc in fuentes)


def unir_fuentes(listas):
    """Une fuentes de varios objetos: una entrada por documento."""
    orden, locs = [], {}
    for k, loc in (f for lista in listas for f in lista):
        if k not in locs:
            orden.append(k)
            locs[k] = []
        if loc and loc not in locs[k]:
            locs[k].append(loc)
    return [(k, juntar_paginas(locs[k])) for k in orden]


def juntar_paginas(locs):
    """Une localizadores; si todos son páginas, una sola lista ordenada."""
    if locs and all(re.match(r"pp?\.~", loc) for loc in locs):
        n = sorted({int(x) for loc in locs for x in re.findall(r"\d+", loc)})
        if len(n) == 1:
            return "p.~%d" % n[0]
        return "pp.~" + ", ".join(str(x) for x in n[:-1]) + " y~%d" % n[-1]
    return "; ".join(locs)


# --- Fallas de la línea base MySQL, verificadas contra ab6a6ec ---------------
def referencias():
    refs, cache = {}, {}
    with open(os.path.join(HERE, "referencias_mysql.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["path"] not in cache:
                cache[r["path"]] = git("show", "%s:%s" % (BASE, r["path"])).split("\n")
            linea = cache[r["path"]][int(r["line"]) - 1]
            if r["snippet"] not in linea:
                falla("%s:%s:%s no contiene «%s»" % (BASE, r["path"], r["line"], r["snippet"]))
            refs.setdefault(int(r["check"]), []).append(r)
    return refs


def ref_corta(r):
    ruta = r["path"][len(PREFIJO):] if r["path"].startswith(PREFIJO) else r["path"]
    return "%s:%s" % (ruta, r["line"])


# --- Líneas de los scripts ---------------------------------------------------
def buscar(ruta, patron):
    with open(os.path.join(ROOT, ruta), encoding="utf-8") as f:
        for i, linea in enumerate(f, 1):
            if patron in linea:
                return "%s:%d" % (ruta, i)
    return None


def script_prueba(tid):
    return (buscar("pruebas/mysql/pruebas.sql", "('%s'," % tid)
            or buscar("pruebas/mysql/pruebas_admin.sql", "('%s'," % tid)
            or buscar("pruebas/mysql/run_tests.sh", "concurrente %s " % tid)
            or buscar("pruebas/mysql/run_tests.sh", "brecha %s " % tid)
            or buscar("pruebas/mysql/run_tests.sh", "registrar %s " % tid)
            or falla("no se encontró el script de la prueba %s" % tid))


# --- El modelo es el de main --------------------------------------------------
def verificar_modelo():
    archivos = [f for f in git("ls-tree", "-r", "--name-only", MAIN, "modelo", "informe").split() if MODELO.match(f)]
    if len(archivos) < 20:
        falla("en %s solo hay %d archivos del modelo" % (MAIN, len(archivos)))
    for f in archivos:
        main = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (MAIN, f)], capture_output=True, check=True).stdout
        with open(os.path.join(ROOT, f), "rb") as fh:
            if fh.read() != main:
                falla("%s difiere del de main (%s): el modelo debe ser el mismo en las dos ramas" % (f, MAIN))
    return len(archivos)


def main():
    refs = referencias()
    n_modelo = verificar_modelo()

    # PostgreSQL (main)
    pg = {}
    for v in ("16", "17"):
        pg[v] = {r[0]: r for r in csv.reader(io.StringIO(git("show", "%s:resultados/postgres/resultado-pg%s.csv" % (MAIN, v))))}
    pmeta = metadatos_de(git("show", "%s:resultados/postgres/metadatos.txt" % MAIN))

    # MySQL (esta rama)
    my = {r[0]: dict(zip(["id", "grupo", "ref", "desc", "esperado", "obtenido", "resultado", "mecanismo",
                          "categoria", "usuarios"], r)) for r in leer_csv("mysql", "resultado-mysql84.csv")[1:]}
    with open(os.path.join(RES, "mysql", "metadatos.txt"), encoding="utf-8") as f:
        mmeta = metadatos_de(f.read())
    faltan = sorted(set(pg["16"]) - set(my))
    if faltan:
        falla("pruebas de main sin equivalente en MySQL: %s" % ", ".join(faltan))
    sobran = sorted(set(my) - set(pg["16"]) - SOLO_MYSQL)
    if sobran:
        falla("pruebas de MySQL que no están en main ni son solo de MySQL: %s" % ", ".join(sobran))
    for t, r in my.items():
        if r["categoria"] == "falla":
            falla("la prueba %s falla en MySQL: %s" % (t, r["obtenido"]))
        if t.startswith("G") and r["categoria"] != "brecha conocida":
            falla("la brecha %s ya no se confirma: revisar su clasificación" % t)

    por_objeto = {}
    for o in catalogo.OBJETOS:
        for t in o.get("pruebas", []):
            por_objeto.setdefault(t, []).append(o)
            if t not in my:
                falla("el objeto %s cita la prueba %s, que no existe" % (o["objeto"], t))
    for d in catalogo.DECLARATIVAS:
        for t in d["pruebas"]:
            if t not in my:
                falla("la regla «%s» cita la prueba %s, que no existe" % (d["regla"], t))

    filas = []
    for t in my:
        r = my[t]
        objs = por_objeto.get(t, [])
        fuentes = unir_fuentes([o["fuentes"] for o in objs] + [catalogo.PRUEBAS.get(t, {}).get("fuentes", [])])
        m = re.match(r"Comprobación (\d+)", r["ref"])
        mysql = refs.get(int(m.group(1)), []) if m else []
        decisiones = sorted(set(re.findall(r"BNA-[A-Z-]+[A-Z]", r["esperado"])))
        decision = catalogo.DECISIONES.get(t)
        if not (fuentes or mysql or decisiones or decision):
            falla("la prueba %s no tiene fuente en el catálogo" % t)
        filas.append(dict(
            id=t, grupo=r["grupo"], afirmacion=r["desc"], regla=r["ref"], fuentes=fuentes, mysql=mysql,
            decisiones=decisiones, decision=decision, script=script_prueba(t), esperado=r["esperado"],
            obtenido=r["obtenido"], mecanismo=r["mecanismo"], categoria=r["categoria"],
            pg16=pg["16"][t][6] if t in pg["16"] else "—", pg17=pg["17"][t][6] if t in pg["17"] else "—"))

    escribir(filas, refs)
    escribir_reglas()
    escribir_comparacion(filas)
    escribir_brechas(my)

    sql = open(os.path.join(ROOT, "sql", "bna_core.sql"), encoding="utf-8").read()
    definer = r"CREATE DEFINER = '[^']+'@'%'(?: SQL SECURITY DEFINER)? "
    comunes = [f for f in filas if f["id"] not in SOLO_MYSQL]
    stats = dict(
        triggers=len(re.findall(definer + "TRIGGER ", sql)),
        procedimientos=len(re.findall(definer + "PROCEDURE ", sql)),
        funciones=len(re.findall(definer + "FUNCTION ", sql)),
        vistas=len(re.findall(definer + "VIEW ", sql)), eventos=len(re.findall(definer + "EVENT ", sql)),
        tablas=sql.count("CREATE TABLE "), indices=sql.count("CREATE INDEX ") + sql.count("CREATE UNIQUE INDEX "),
        funcionales=sql.count("CREATE UNIQUE INDEX "), lineassql=sql.count("\n"),
        lineasprogramacion=open(os.path.join(INF, "mysql-programacion.sql"), encoding="utf-8").read().count("\n"),
        pruebasfecha=fecha_larga(mmeta["fecha"]), pruebascommit=mmeta["commit"].split()[0][:7],
        mysqlversion=mmeta["mysql"], maincommit=MAIN, pgpruebascommit=pmeta["commit"].split()[0][:7],
        pgfecha=fecha_larga(pmeta["fecha"]), comunes=len(comunes),
        comunesigual=sum(1 for f in comunes if f["pg16"] == f["pg17"] and (
            (f["pg16"] == "pasa" and f["categoria"].startswith("pasa"))
            or (f["pg16"] == "N/A" and f["categoria"] == "N/A"))),
        archivosmodelo=n_modelo, matrizfilas=len(filas), referenciasmysql=sum(len(v) for v in refs.values()),
        reglas=sum(1 for o in catalogo.OBJETOS if "grupo" not in o) + len(catalogo.DECLARATIVAS),
        brechas=len(catalogo.BRECHAS))
    with open(os.path.join(INF, "mysql-stats.tex"), "w", encoding="utf-8") as f:
        f.write("% Generated by trazabilidad/matriz.py (rama mysql)\n")
        for k, v in stats.items():
            f.write("\\expandafter\\def\\csname statmy:%s\\endcsname{%s}\n" % (k, v))
    print("Matriz MySQL: %d filas; %d referencias a %s verificadas; modelo idéntico a %s (%d archivos)" % (
        len(filas), stats["referenciasmysql"], BASE, MAIN, n_modelo))


# --- Salidas ------------------------------------------------------------------
def fuente_texto(f):
    partes = []
    if f["fuentes"]:
        partes.append(texto_fuente(f["fuentes"]))
    if f["mysql"]:
        partes.append("MySQL %s: %s" % (BASE, ", ".join(ref_corta(r) for r in f["mysql"])))
    if f["decisiones"]:
        partes.append("Decisión del informe: " + ", ".join(f["decisiones"]))
    if f["decision"]:
        partes.append("Decisión del informe: " + f["decision"])
    return "; ".join(partes)


def pg_resultado(r16, r17):
    """Un solo valor si PostgreSQL 16 y 17 coinciden."""
    return r16 if r16 == r17 else "%s/%s" % (r16, r17)


def escribir(filas, refs):
    cols = ["id", "afirmacion", "regla", "fuente", "script", "mecanismo", "esperado", "obtenido", "mysql84",
            "pg16", "pg17"]
    with open(os.path.join(RES, "trazabilidad.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for f in filas:
            w.writerow([f["id"], f["afirmacion"], f["regla"], fuente_texto(f), f["script"], f["mecanismo"],
                        f["esperado"], f["obtenido"], f["categoria"], f["pg16"], f["pg17"]])

    def celda(s):
        return s.replace("|", "\\|").replace("\n", " ")
    md = ["# Matriz de trazabilidad (versión MySQL)", "",
          "Generada por `trazabilidad/matriz.py` a partir de `trazabilidad/catalogo.py`,",
          "`trazabilidad/referencias_mysql.csv`, `resultados/mysql/` y los resultados de PostgreSQL",
          "de la rama main (commit %s). Las páginas son las del archivo PDF de cada documento; las" % MAIN,
          "fallas MySQL se citan como `%s:<ruta>:<línea>`, con la ruta relativa a `%s`." % (BASE, PREFIJO), "",
          "| ID | Afirmación o regla | Fuente | Script | Mecanismo | Esperado | Obtenido | MySQL 8.4 | PG 16 | PG 17 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        md.append("| %s |" % " | ".join(celda(x) for x in [
            f["id"], f["afirmacion"] + (" (%s)" % f["regla"] if f["regla"] else ""), fuente_texto(f),
            "`%s`" % f["script"], f["mecanismo"], f["esperado"], f["obtenido"], f["categoria"], f["pg16"], f["pg17"]]))
    with open(os.path.join(RES, "trazabilidad.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    # Anexo del informe
    grupos = {"L": "Carga y configuración", "M": "Fallas de la línea base MySQL", "C": "Concurrencia",
              "F": "Objetos portados e implementados", "R": "Regresión", "G": "Brechas conocidas de MySQL"}
    lineas, actual = ["% Generated by trazabilidad/matriz.py (rama mysql)"], None
    for f in filas:
        if f["id"][0] != actual:
            actual = f["id"][0]
            if len(lineas) > 1:
                lineas.append(r"\addlinespace")
            lineas.append(r"\multicolumn{7}{@{}l}{\textit{%s}} \\" % grupos[actual])
        fuente = []
        if f["fuentes"]:
            fuente.append(cita(f["fuentes"]))
        if f["mysql"]:
            fuente.append("MySQL: " + ", ".join(nm(ref_corta(r).replace("BD/99_bna_unificado.sql", "99"))
                                               for r in f["mysql"]))
        if f["decisiones"]:
            fuente.append("Decisión: " + ", ".join(f["decisiones"]))
        if f["decision"]:
            fuente.append("Decisión: " + tex(f["decision"]))
        afirm = tex(f["afirmacion"]) + (r" \textit{(%s)}" % tex(f["regla"]) if f["regla"] else "")
        eo = r"\textit{E:} %s \newline \textit{O:} %s" % (tex(f["esperado"]), tex(f["obtenido"]))
        lineas.append(r"%s & %s & %s & %s & %s & %s & %s \\" % (
            tex(f["id"]), afirm, "; ".join(fuente), nm(f["script"]), eo, ABREV[f["categoria"]],
            pg_resultado(ABREV.get(f["pg16"], f["pg16"]), ABREV.get(f["pg17"], f["pg17"]))))
    with open(os.path.join(INF, "mysql-trazabilidad.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")

    md = ["# Fallas de la línea base MySQL", "",
          "Cada línea se comprobó con `git show %s:<ruta>` al generar la matriz." % BASE, "",
          "| Comprobación | Bug | Ruta:línea | Fragmento | Explicación |", "|---|---|---|---|---|"]
    for n in sorted(refs):
        for r in refs[n]:
            md.append("| %s | %s | `%s` | `%s` | %s |" % (n, r["bug"], ref_corta(r), celda(r["snippet"]),
                                                          celda(r["explanation"])))
    with open(os.path.join(RES, "referencias_mysql.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")


def primera_oracion(s):
    m = re.match(r"(.+?)[.;](\s|$)", s)
    return m.group(1) + "." if m else s


def escribir_reglas():
    """Cómo se cumple cada regla en cada gestor (cuadro comparativo)."""
    lineas = ["% Generated by trazabilidad/matriz.py (rama mysql)"]
    for o in catalogo.OBJETOS:
        if "grupo" in o:
            if len(lineas) > 1:
                lineas.append(r"\addlinespace")
            lineas.append(r"\multicolumn{5}{@{}l}{\textit{%s}} \\" % o["grupo"])
            continue
        lineas.append(r"%s & %s & %s \newline {\footnotesize %s} & %s & %s \\" % (
            primera_oracion(o["regla"]), o["pg"], o["my"], o["my_objetos"], o["vale"], ", ".join(o["pruebas"])))
    lineas.append(r"\addlinespace")
    lineas.append(r"\multicolumn{5}{@{}l}{\textit{Restricciones declarativas y tipos}} \\")
    for d in catalogo.DECLARATIVAS:
        lineas.append(r"%s & %s & %s & %s & %s \\" % (d["regla"], d["pg"], d["my"], d["vale"], ", ".join(d["pruebas"])))
    with open(os.path.join(INF, "mysql-reglas.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")


def escribir_comparacion(filas):
    """Resultado de cada prueba en PostgreSQL 16 y 17 y en MySQL 8.4."""
    grupos = {"L": "Carga y configuración", "M": "Fallas de la línea base MySQL", "C": "Concurrencia",
              "F": "Objetos portados e implementados", "R": "Regresión", "G": "Brechas conocidas (solo MySQL)"}
    pgtxt = {"pasa": "Pasa", "falla": "Falla", "N/A": "N/A", "—": "—"}
    lineas, actual = ["% Generated by trazabilidad/matriz.py (rama mysql)"], None
    for f in filas:
        if f["id"][0] != actual:
            actual = f["id"][0]
            if len(lineas) > 1:
                lineas.append(r"\addlinespace")
            lineas.append(r"\multicolumn{5}{@{}l}{\textit{%s}} \\" % grupos[actual])
        lineas.append(r"%s & %s & %s & %s & %s \\" % (
            f["id"] + (r"\textsuperscript{*}" if f["id"] in SOLO_MYSQL else ""), tex(f["afirmacion"]),
            pgtxt[f["pg16"]], pgtxt[f["pg17"]], CATEGORIA[f["categoria"]]))
    with open(os.path.join(INF, "mysql-comparacion.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")


def escribir_brechas(my):
    lineas = ["% Generated by trazabilidad/matriz.py (rama mysql)"]
    for b in catalogo.BRECHAS:
        lineas.append(r"%s & %s & %s & %s \\" % (b["id"], b["que"], b["mitigacion"], tex(my[b["id"]]["obtenido"])))
    with open(os.path.join(INF, "mysql-brechas.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
