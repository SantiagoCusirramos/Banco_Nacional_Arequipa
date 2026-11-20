#!/usr/bin/env python3
"""Proxy HTTP local para usar la app Chaski contra el clúster sin VPN en el celular.

La PC (conectada a la VPN) escucha en 127.0.0.1:8020 y reenvía cada petición a la API de Chaski
publicada en el Ingress, con el Host que Traefik espera. Con el celular por USB:

    python3 billetera-chaski/proxy_vpn.py            # en la PC, con la VPN activa
    adb reverse tcp:8020 tcp:8020                     # el localhost:8020 del celular llega aquí

y en la app (engranaje ⚙ de la pantalla de ingreso) el servidor http://localhost:8020.
Solo biblioteca estándar. No registra cuerpos, consultas ni cabeceras (el celular y el PIN van en
el cuerpo). Para otro destino: --destino http://bna-billetera.<IP>.sslip.io
"""
import argparse
import http.client
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

POR_OMISION = "http://bna-billetera.172.16.10.31.sslip.io"
SALTO_A_SALTO = {"connection", "keep-alive", "proxy-connection", "transfer-encoding", "upgrade", "te", "trailer", "host"}


def crear_manejador(destino):
    partes = urlsplit(destino)
    if partes.scheme not in ("http", "https") or not partes.hostname or partes.path not in ("", "/"):
        sys.exit("--destino debe ser http(s)://host[:puerto], sin ruta")
    Conexion = http.client.HTTPSConnection if partes.scheme == "https" else http.client.HTTPConnection

    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _reenviar(self):
            largo = int(self.headers.get("Content-Length") or 0)
            cuerpo = self.rfile.read(largo) if largo else None
            cabeceras = {k: v for k, v in self.headers.items() if k.lower() not in SALTO_A_SALTO}
            cabeceras["Host"] = partes.netloc
            try:
                conexion = Conexion(partes.hostname, partes.port, timeout=30)
                conexion.request(self.command, self.path, body=cuerpo, headers=cabeceras)
                respuesta = conexion.getresponse()
                datos = respuesta.read()
            except OSError as error:
                self.send_error(502, f"Sin conexión con {partes.netloc} ({type(error).__name__}); ¿está activa la VPN?")
                return
            self.send_response(respuesta.status, respuesta.reason)
            for k, v in respuesta.getheaders():
                if k.lower() not in SALTO_A_SALTO and k.lower() != "content-length":
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)
            conexion.close()

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _reenviar

        def log_message(self, formato, *args):
            # Solo método, ruta sin consulta y código: nada del cuerpo.
            ruta = self.path.split("?", 1)[0]
            sys.stderr.write(f"{self.command} {ruta} {args[1] if len(args) > 1 else ''}\n")

    return Manejador


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--destino", default=POR_OMISION, help=f"API de Chaski (por omisión {POR_OMISION})")
    p.add_argument("--puerto", type=int, default=8020, help="puerto local (por omisión 8020)")
    a = p.parse_args()
    servidor = ThreadingHTTPServer(("127.0.0.1", a.puerto), crear_manejador(a.destino.rstrip("/")))
    print(f"http://127.0.0.1:{a.puerto} → {a.destino} (Ctrl-C para salir)", file=sys.stderr)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
