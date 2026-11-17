"""Parche aislado CR03. Solo acepta la fuente EVA fijada y registra ambos hashes."""
import hashlib

OLD = '''        if r.is_success:
            self._terminar(fila, intentos, "ENTREGADO", None)
            return 1
'''
NEW = '''        if r.is_success:
            try:
                acuse = r.json()
            except ValueError:
                acuse = None
            if (r.status_code == 200 and isinstance(acuse, dict)
                    and acuse.get("recibido") is True
                    and acuse.get("idOperacion") == contenido["idOperacion"]):
                self._terminar(fila, intentos, "ENTREGADO", None)
                return 1
            self._terminar(fila, intentos, "ERROR", "ACUSE_SOL_INVALIDO")
            return 0
'''


def apply(path):
    original = path.read_bytes()
    source = original.decode()
    if source.count(OLD) != 1:
        raise ValueError('EVA cambió; parche no aplicable de forma inequívoca.')
    path.write_text(source.replace(OLD, NEW))
    return {'path': 'EVALUACION/envios.py', 'reason': 'Validar acuse CR03, no solo HTTP 2xx',
            'before': hashlib.sha256(original).hexdigest(),
            'after': hashlib.sha256(path.read_bytes()).hexdigest()}


def apply_fixture(path):
    """Actualizar exclusivamente el doble de tests al acuse real documentado por SOL."""
    old='return httpx.Response(estado, json={"recibido": estado == 200})'
    new='return httpx.Response(estado, json={"recibido": estado == 200, "idOperacion": peticion.headers["X-Idempotency-Key"]})'
    original=path.read_bytes()
    source=original.decode()
    if source.count(old)!=1:raise ValueError('Fixture EVA cambió; requiere revisión.')
    path.write_text(source.replace(old,new))
    return {'path':'EVALUACION/tests/ayudas.py','reason':'Doble SOL responde con idOperacion como API real',
            'before':hashlib.sha256(original).hexdigest(),'after':hashlib.sha256(path.read_bytes()).hexdigest()}
