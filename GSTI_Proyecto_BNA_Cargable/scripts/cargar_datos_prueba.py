#!/usr/bin/env python3
"""Carga datos de prueba FICTICIOS y reproducibles. Solo usa la librería estándar de Python.

Qué hace (es idempotente: se puede ejecutar varias veces):
  1. RENIEC: registra 3 ciudadanos ficticios y carga huellas sintéticas (se convierten en plantillas reales con NBIS).
  2. Banco: registra clientes reales a través de la ruta del laboratorio (Panel -> Bus -> Clientes -> RENIEC -> Bus -> Core).

Uso (con el sistema levantado):  python scripts/cargar_datos_prueba.py
Lee RENIEC_URL, CLIENTES_URL y las credenciales del archivo .env (o de variables de entorno).
Los rostros NO se cargan aquí: no hay imágenes faciales sintéticas utilizables; súbalos desde la interfaz de RENIEC.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer_env() -> dict:
    valores = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip()
    valores.update({k: v for k, v in os.environ.items() if k in valores or k.startswith(("RENIEC_", "CLIENTES_", "PUERTO_"))})
    return valores


ENV = leer_env()
RENIEC_URL = os.getenv("RENIEC_URL_HOST", f"http://localhost:{ENV.get('PUERTO_RENIEC', '8002')}")
CLIENTES_URL = os.getenv("CLIENTES_URL_HOST", f"http://localhost:{ENV.get('PUERTO_CLIENTES', '8001')}")
RENIEC_AUTH = (ENV.get("RENIEC_ADMIN_USER", "admin"), ENV.get("RENIEC_ADMIN_PASSWORD", ""))
PANEL_AUTH = (ENV.get("CLIENTES_PANEL_USER", "panel"), ENV.get("CLIENTES_PANEL_PASSWORD", ""))


def llamar(metodo, url, auth, cuerpo_json=None, multipart=None):
    cabeceras = {"Authorization": "Basic " + base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()}
    datos = None
    if cuerpo_json is not None:
        datos = json.dumps(cuerpo_json).encode()
        cabeceras["Content-Type"] = "application/json"
    elif multipart is not None:
        frontera = uuid.uuid4().hex
        nombre, contenido = multipart
        datos = (f"--{frontera}\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"{nombre}\"\r\n"
                 f"Content-Type: image/png\r\n\r\n").encode() + contenido + f"\r\n--{frontera}--\r\n".encode()
        cabeceras["Content-Type"] = f"multipart/form-data; boundary={frontera}"
    req = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except urllib.error.URLError as e:
        sys.exit(f"No se pudo conectar a {url}: {e.reason}. ¿Está levantado el sistema (docker compose up -d --build)?")


CIUDADANOS = [
    {"numero_documento": "70000001", "nombres": "Juan Carlos", "apellidos": "Pérez Quispe", "fecha_nacimiento": "1990-05-14", "genero": "M"},
    {"numero_documento": "70000002", "nombres": "María Elena", "apellidos": "Mamani Condori", "fecha_nacimiento": "1995-11-02", "genero": "F"},
    {"numero_documento": "70000003", "nombres": "Luis Alberto", "apellidos": "Huamán Ccama", "fecha_nacimiento": "1988-03-21", "genero": "M"},
]
HUELLAS = {"70000001": "huella_A.png", "70000002": "huella_B.png"}  # 70000003 queda sin plantillas

CLIENTES = [
    {"modulo_origen": "AGENCIAS", "tipo_documento": "DNI", "numero_documento": "70000001", "nombres": "Juan Carlos", "apellidos": "Pérez Quispe",
     "fecha_nacimiento": "1990-05-14", "ingreso_mensual": 3500.00, "direccion": "Av. Parra 345, Cercado, Arequipa", "correo": "juan.perez@example.com", "telefono": "954000001"},
    {"modulo_origen": "AGENCIAS", "tipo_documento": "PASAPORTE", "numero_documento": "AB123456", "nombres": "Carlos", "apellidos": "Ramírez Ortiz",
     "fecha_nacimiento": "1985-07-09", "ingreso_mensual": 4200.00, "direccion": "Calle San Francisco 210, Arequipa", "correo": "carlos.ramirez@example.com", "telefono": "+51954000020"},
    {"modulo_origen": "AGENCIAS", "tipo_documento": "PTP", "numero_documento": "PTP2024001", "nombres": "Andrea", "apellidos": "Gómez Rivero",
     "fecha_nacimiento": "1992-01-30", "ingreso_mensual": 2600.00, "direccion": "Urb. Cayma Mz C Lt 5, Arequipa", "correo": "andrea.gomez@example.com", "telefono": "954000021"},
]


def main() -> None:
    if not RENIEC_AUTH[1] or not PANEL_AUTH[1]:
        sys.exit("Faltan credenciales: copie .env.example a .env y complete las claves.")
    print(f"RENIEC:   {RENIEC_URL}\nClientes: {CLIENTES_URL}\n")

    print("== RENIEC: ciudadanos ficticios")
    for c in CIUDADANOS:
        st, r = llamar("POST", f"{RENIEC_URL}/admin/api/ciudadanos", RENIEC_AUTH, cuerpo_json=c)
        print(f"  {c['numero_documento']} {c['nombres']} {c['apellidos']}: " + ("creado" if st == 201 else "ya existía" if st == 409 else f"ERROR {st} {r}"))

    print("== RENIEC: huellas sintéticas -> plantillas ISO 19794-2")
    for dni, archivo in HUELLAS.items():
        contenido = (RAIZ / "datos_prueba" / "huellas" / archivo).read_bytes()
        st, r = llamar("POST", f"{RENIEC_URL}/admin/api/ciudadanos/{dni}/biometria/huella", RENIEC_AUTH, multipart=(archivo, contenido))
        print(f"  {dni} <- {archivo}: " + (f"plantilla guardada ({r.get('minucias')} minucias, NFIQ2 {r.get('calidad_nfiq2')})" if st == 200 else f"ERROR {st} {r}"))

    print("== Core: clientes del banco (vía Panel -> Bus -> Clientes)")
    for c in CLIENTES:
        st, r = llamar("POST", f"{CLIENTES_URL}/panel/api/lab/registrar", PANEL_AUTH, cuerpo_json=c)
        resp = r.get("respuesta", r)
        estado = "registrado" if r.get("http") == 201 else "ya existía" if r.get("http") == 409 else f"ERROR {r.get('http', st)} {resp}"
        print(f"  {c['tipo_documento']} {c['numero_documento']}: {estado}")

    print("\nListo. DNI de prueba:")
    print("  70000001  en RENIEC y cliente del banco (huella A cargada)")
    print("  70000002  en RENIEC, NO cliente (huella B cargada) -> úselo para probar el registro en vivo")
    print("  70000003  en RENIEC, NO cliente, sin biometría")
    print("  70000099  no existe en RENIEC")
    print("  Pasaporte AB123456 y PTP PTP2024001: clientes del banco (no verificados en RENIEC)")


if __name__ == "__main__":
    main()
