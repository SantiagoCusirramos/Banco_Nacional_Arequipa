# Combines the rows written by run_tests.sh (one per test and user) into
#   resultados/mysql/resultado-mysql84.csv   one row per test ID
#   resultados/mysql/resultados.md           full table, for the repository
#   informe/mysql-pruebas-stats.tex          counts for the report (\statmy)
# A test ID passes only if all its rows pass (bna_app_user and, for the
# rules protected by privilege, bna_admin_user). The category says how the
# rule holds in MySQL: «pasa» (declarative or trigger, as in main), «pasa vía
# privilegio», «pasa vía procedimiento», «brecha conocida» (G tests, which
# confirm a gap) or «N/A».
# Usage: combinar.py <out_dir> <informe> <version>
import csv
import os
import re
import sys

out_dir, model_dir, version = sys.argv[1:]

ORDER = {"L": 0, "M": 1, "C": 2, "F": 3, "R": 4, "G": 5}
CORTO = {"bna_app_user": "app", "bna_admin_user": "admin", "root": "root"}


def key(test_id):
    m = re.match(r"([A-Z])(\d+)(\w*)", test_id)
    return ORDER[m.group(1)], int(m.group(2)), m.group(3)


def unescape(s):
    """Undo the escaping of mysql --batch (\\t, \\n, \\\\)."""
    return re.sub(r"\\(.)", lambda m: {"t": "\t", "n": "\n", "0": "\0"}.get(m.group(1), m.group(1)), s)


rows = {}
with open(os.path.join(out_dir, "resultado.tsv"), encoding="utf-8") as f:
    for line in f:
        tid, usuario, grupo, ref, desc, mec, esperado, obtenido, res = [unescape(x) for x in line.rstrip("\n").split("\t")]
        rows.setdefault(tid, []).append(dict(usuario=usuario, grupo=grupo, ref=ref, desc=desc, mec=mec,
                                             esperado=esperado, obtenido=obtenido, res=res))


def categoria(rs):
    res = {r["res"] for r in rs}
    mecs = [r["mec"] for r in rs]
    if res == {"N/A"}:
        return "N/A"
    if "falla" in res:
        return "falla"
    if "brecha" in mecs:
        return "brecha conocida"
    if "privilegio" in mecs and "procedimiento" in mecs:
        return "pasa vía procedimiento y privilegio"
    if "privilegio" in mecs:
        return "pasa vía privilegio"
    if "procedimiento" in mecs:
        return "pasa vía procedimiento"
    return "pasa"


def unir(rs, campo):
    vals = [r[campo] for r in rs]
    if len(set(vals)) == 1:
        return vals[0]
    return "; ".join("%s: %s" % (CORTO.get(r["usuario"], r["usuario"]), r[campo]) for r in rs)


ids = sorted(rows, key=key)
tabla = []
for t in ids:
    rs = rows[t]
    mecs = list(dict.fromkeys(r["mec"] for r in rs))
    tabla.append(dict(id=t, grupo=rs[0]["grupo"], ref=rs[0]["ref"], desc=rs[0]["desc"],
                      esperado=unir(rs, "esperado"), obtenido=unir(rs, "obtenido"),
                      resultado="N/A" if categoria(rs) == "N/A" else ("falla" if categoria(rs) == "falla" else "pasa"),
                      mecanismo=" + ".join(mecs), categoria=categoria(rs),
                      usuarios=", ".join(dict.fromkeys(CORTO.get(r["usuario"], r["usuario"]) for r in rs))))

with open(os.path.join(out_dir, "resultado-mysql84.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["id", "grupo", "referencia", "descripcion", "esperado", "obtenido", "resultado", "mecanismo",
                "categoria", "usuarios"])
    for r in tabla:
        w.writerow([r[k] for k in ("id", "grupo", "ref", "desc", "esperado", "obtenido", "resultado", "mecanismo",
                                   "categoria", "usuarios")])

cuenta = {}
for r in tabla:
    cuenta[r["categoria"]] = cuenta.get(r["categoria"], 0) + 1
comunes = [r for r in tabla if not r["id"].startswith("G")]


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ")


md = ["# Resultados de las pruebas de la base integrada en MySQL", "",
      "Generado por `pruebas/mysql/run_tests.sh`. Los ID son los de la rama main (PostgreSQL);",
      "L02, M20c, F32 y G01 a G05 son solo de MySQL. Un ID pasa si pasan todas sus filas",
      "(`app` = bna_app_user, `admin` = bna_admin_user). Las G confirman una brecha conocida.", "",
      "- MySQL %s: %s." % (version, ", ".join("%d %s" % (n, c) for c, n in sorted(cuenta.items()))), "",
      "| ID | Grupo | Referencia | Prueba | Mecanismo | Esperado | Obtenido | Resultado |",
      "|---|---|---|---|---|---|---|---|"]
for r in tabla:
    md.append("| %s |" % " | ".join(cell(x) for x in (r["id"], r["grupo"], r["ref"], r["desc"], r["mecanismo"],
                                                       r["esperado"], r["obtenido"], r["categoria"])))
with open(os.path.join(out_dir, "resultados.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

stats = dict(
    pruebas=len(tabla), pruebascomunes=len(comunes),
    pruebassolomysql=len([r for r in tabla if r["id"] in ("L02", "M20c", "F32") or r["id"].startswith("G")]),
    pasan=sum(1 for r in tabla if r["categoria"].startswith("pasa")),
    pasadirecto=cuenta.get("pasa", 0), pasaprivilegio=cuenta.get("pasa vía privilegio", 0),
    pasaprocedimiento=cuenta.get("pasa vía procedimiento", 0) + cuenta.get("pasa vía procedimiento y privilegio", 0),
    brechas=cuenta.get("brecha conocida", 0), na=cuenta.get("N/A", 0), fallan=cuenta.get("falla", 0),
    version=version)
with open(os.path.join(model_dir, "mysql-pruebas-stats.tex"), "w", encoding="utf-8") as f:
    f.write("% Generated by pruebas/mysql/run_tests.sh\n")
    for k, v in stats.items():
        f.write("\\expandafter\\def\\csname statmy:%s\\endcsname{%s}\n" % (k, v))
print("   MySQL %s: %s" % (version, ", ".join("%d %s" % (n, c) for c, n in sorted(cuenta.items()))))
print("Resultados en %s" % os.path.join(out_dir, "resultados.md"))
