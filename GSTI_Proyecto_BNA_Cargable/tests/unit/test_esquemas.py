"""Reglas de validación de datos (compartidas por Clientes y Core)."""
import pytest
from pydantic import ValidationError

from shared.esquemas import DatosCliente, ValidarBiometriaIn, ValidarDocumentoIn

VALIDO = dict(modulo_origen="AGENCIAS", tipo_documento="DNI", numero_documento="12345678", nombres="Juan", apellidos="Pérez",
              fecha_nacimiento="1990-05-14", ingreso_mensual=1500.5, direccion="Av. Siempre Viva 123",
              correo="juan@example.com", telefono="954000111")


def con(**cambios):
    return {**VALIDO, **cambios}


def test_registro_valido():
    d = DatosCliente(**VALIDO)
    assert d.correo == "juan@example.com" and str(d.ingreso_mensual) == "1500.5"


@pytest.mark.parametrize("campo,valor", [
    ("numero_documento", 12345678),          # los documentos son cadenas, no números JSON
    ("telefono", 954000111),                  # ídem para el teléfono
    ("numero_documento", "1234567"),          # DNI de 7 dígitos
    ("numero_documento", "1234567A"),         # DNI con letras
    ("correo", "sin-arroba"),
    ("correo", "a@b"),
    ("fecha_nacimiento", "14/05/1990"),       # formato de fecha incorrecto
    ("fecha_nacimiento", "2999-01-01"),       # fecha futura
    ("fecha_nacimiento", "1800-01-01"),       # fuera de rango
    ("ingreso_mensual", -1),
    ("ingreso_mensual", 1.234),               # más de 2 decimales
    ("modulo_origen", "NO_EXISTE"),
    ("tipo_documento", "CARNET"),
    ("telefono", "abc"),
    ("nombres", "   "),
])
def test_registro_invalido(campo, valor):
    with pytest.raises(ValidationError):
        DatosCliente(**con(**{campo: valor}))


def test_modulo_origen_es_obligatorio():
    datos = dict(VALIDO)
    datos.pop("modulo_origen")
    with pytest.raises(ValidationError):
        DatosCliente(**datos)


def test_no_se_aceptan_campos_extra():
    with pytest.raises(ValidationError):
        DatosCliente(**con(genero="M"))


def test_formato_documento_por_tipo():
    assert DatosCliente(**con(tipo_documento="PASAPORTE", numero_documento="ab123456")).numero_documento == "AB123456"
    assert DatosCliente(**con(tipo_documento="PTP", numero_documento="PTP2024001")).numero_documento == "PTP2024001"
    with pytest.raises(ValidationError):
        DatosCliente(**con(tipo_documento="PASAPORTE", numero_documento="A1"))


def test_telefono_se_normaliza_pero_sigue_siendo_cadena():
    assert DatosCliente(**con(telefono="+51 954-000-111")).telefono == "+51954000111"


def test_validar_documento_solo_pide_cuatro_campos():
    v = ValidarDocumentoIn(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="12345678", fecha_nacimiento="1990-05-14")
    assert v.numero_documento == "12345678"


BIO_FACIAL = dict(modulo_origen="BANCA_LINEA", tipo_documento="DNI", numero_documento="12345678", tipo_biometria="FACIAL",
                  formato="ARCFACE_EMBEDDING", template=[0.1] * 512)
BIO_HUELLA = dict(modulo_origen="CAJERO_AUTOMATICO", tipo_documento="DNI", numero_documento="12345678", tipo_biometria="HUELLA",
                  formato="ISO_19794_2_2005", codificacion="base64", template="Rk1SAAAAAAAAAAAAAAAAAAAA")


def test_biometria_valida():
    assert ValidarBiometriaIn(**BIO_FACIAL).tipo_biometria == "FACIAL"
    assert ValidarBiometriaIn(**BIO_HUELLA).codificacion == "base64"


@pytest.mark.parametrize("base,cambios", [
    (BIO_FACIAL, dict(tipo_documento="PASAPORTE", numero_documento="AB123456")),  # solo DNI
    (BIO_FACIAL, dict(template=[0.1] * 100)),                                      # dimensión incorrecta
    (BIO_FACIAL, dict(template="Rk1S")),                                           # facial exige lista
    (BIO_FACIAL, dict(formato="ISO_19794_2_2005")),                                # formato no corresponde
    (BIO_HUELLA, dict(codificacion=None)),                                         # huella exige base64
    (BIO_HUELLA, dict(template=[0.1] * 512)),                                      # huella exige cadena
    (BIO_HUELLA, dict(formato="ARCFACE_EMBEDDING")),
])
def test_biometria_invalida(base, cambios):
    with pytest.raises(ValidationError):
        ValidarBiometriaIn(**{**base, **cambios})


def test_el_error_de_validacion_no_repite_la_plantilla():
    """Los mensajes de error no deben incluir el valor recibido (podría ser biometría)."""
    with pytest.raises(ValidationError) as e:
        ValidarBiometriaIn(**{**BIO_FACIAL, "template": [0.123456789] * 100})
    assert "0.123456789" not in str(e.value.errors(include_input=False))
