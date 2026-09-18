# firma-digital

Firma PDFs desde Linux con un token criptográfico (smartcard USB), replicando el
formato que produce Adobe Acrobat en Windows — incluido el sello visible y el
bloqueo del documento tras la firma.

```bash
firmar-pdf documento.pdf documento_firmado.pdf
```

Se abre una ventana con el documento, arrastrás con el mouse el área donde va el
sello, confirmás, ponés el PIN y listo.

## Por qué existe

En Linux, las herramientas habituales para firmar PDF con token **no funcionan**
si la clave privada del token exige reautenticación por operación
(`CKA_ALWAYS_AUTHENTICATE`), que es lo normal en certificados cualificados de
firma. LibreOffice se cuelga y `pdfsig` falla, ambos porque firman a través de
**NSS**, que no implementa el segundo login que exige el estándar PKCS#11.

Este proyecto usa [pyHanko](https://github.com/MatthiasValvekens/pyHanko) contra
PKCS#11 **nativo**, que sí lo maneja. El detalle medido está en
[docs/diagnostico.md](docs/diagnostico.md).

El otro problema es humano: la firma digital no necesita dejar marca en el papel,
pero en las áreas administrativas un documento sin el texto *"Firmado
digitalmente por..."* se considera no firmado. Por eso el sello visible viene por
defecto.

## Instalación

Ver [docs/instalacion.md](docs/instalacion.md). Resumido:

```bash
# middleware del token (ejemplo con Bit4id; instalar SIEMPRE con apt, no dpkg)
sudo apt install ./Bit4id_Middleware.deb

# dependencias
sudo apt install pipx python3-tk mupdf-tools
pipx install 'pyhanko-cli[pkcs11]'
pipx inject pyhanko-cli 'pyhanko[pkcs11]'

# el firmador y el validador
sudo install -m755 firmar-pdf validar-pdf /usr/local/bin/
```

## Uso

```bash
firmar-pdf                                   # todo por ventanas
firmar-pdf doc.pdf                           # salida: doc_firmado.pdf
firmar-pdf doc.pdf otro.pdf                  # nombre de salida explícito
firmar-pdf doc.pdf --caja 1:340,70,560,140   # sin ventana, para lotes
firmar-pdf doc.pdf --invisible               # sin sello visible
firmar-pdf doc.pdf --sin-bloqueo             # sin bloquear los campos
```

Sin argumentos, el recorrido es: elegir el PDF → guardar como (precargado con
`<nombre>_firmado.pdf`) → marcar el área del sello → PIN. Todo en ventanas.

Si indicás el PDF por línea de comandos pero no el destino, se deriva solo
(`documento.pdf` → `documento_firmado.pdf`) sin abrir diálogo. Si el destino ya
existe, corta con un error; `--forzar` lo sobrescribe.

En el selector de área: arrastrás el rectángulo, `<` `>` cambian de página,
`+` `−` y *Ajustar* controlan el zoom, la rueda del mouse hace scroll. **Enter**
firma, **Escape** cancela. Al confirmar imprime el `--caja` equivalente, para
reusarlo en lote.

`--caja` usa **puntos PDF con origen abajo-izquierda** (A4 = 595×842).

El cuerpo de letra del sello se calcula solo: el mayor con el que las tres
líneas entran en el área que marcaste, sin recortarse. `--tamano-fuente` lo fija
a mano si preferís.

El texto se apoya abajo a la izquierda del recuadro, que es lo natural si lo
marcás sobre una línea de firma. `--alineacion` acepta `abajo-izq` (default),
`abajo-centro`, `centro` y `arriba-izq`.

Los bordes que anclan quedan exactos (~2 pt del borde). Las variantes
**centradas son aproximadas**: pyHanko calcula el ancho del bloque con un único
ratio por fuente, y una línea toda en mayúsculas es más ancha que ese promedio,
así que el reparto no queda parejo. Medido con `tools/probar-sello.py`.

Mientras arrastrás, el selector dibuja el sello **como va a quedar**: mismo
cuerpo de letra, misma alineación. El nombre sale de tu certificado, que se lee
sin PIN (los certificados son objetos públicos del token).

El PIN se pide en una ventana cuando usaste el selector visual, y por terminal
en modo lote. `--pin-terminal` fuerza la terminal siempre. **Hay un solo
intento**, a propósito: un PIN equivocado cuenta como fallo contra el token, que
se bloquea a los tres.

## Configuración

Normalmente **no hace falta configurar nada**: el módulo PKCS#11 se busca entre
las rutas conocidas y los objetos del token se detectan solos (un token personal
tiene un único certificado y una única clave).

Si tenés varios tokens o un módulo en una ruta no estándar:

```ini
# ~/.config/firma-digital/config.ini
[token]
lib = /usr/lib/bit4id/libbit4xpki.so
token_label = SecID XXXXXXXXXX
cert_label = DS3
key_label = DS3_Private
```

También sirven los flags `--lib`, `--token-label`, `--cert-label`, `--key-label`
o las variables `FIRMA_LIB`, `FIRMA_TOKEN_LABEL`, `FIRMA_CERT_LABEL`,
`FIRMA_KEY_LABEL`. Para ver las etiquetas reales de tu token:

```bash
pkcs11-tool --module /ruta/al/modulo.so -O -l
```

## Validar un PDF firmado

```bash
validar-pdf                          # elige el archivo y muestra el informe en una ventana
validar-pdf documento_firmado.pdf    # informe en la terminal
```

```
Firma 1 de 1
------------
  Firmante   : NOMBRE DEL FIRMANTE
  Emisor     : SOS TECNOLOGIA Y GESTION DE INFORMACION LTDA
  Fecha      : 2026-09-18 15:02:16 -0300

  [OK   ] Integridad    el documento no fue alterado tras firmar
  [OK   ] Cobertura     la firma abarca todo el archivo
  [OK   ] Confianza     el certificado encadena a una raiz confiable
  [OK   ] Bloqueo       no hubo cambios prohibidos por el bloqueo
```

Sin argumentos abre un selector de archivos y presenta el resultado en una
ventana, con una banda verde o roja según el veredicto. Si le pasás la ruta, el
informe va a la terminal; `--terminal` fuerza ese modo también al elegir por
diálogo.

Devuelve 0 si todas las firmas están bien y 1 si alguna falla, así que sirve en
scripts. Los certificados de las CA salen de `certificados/` (viene con la raíz
del Paraguay y la intermedia de SOS), de `~/.config/firma-digital/ca/` y de los
que pases con `--ca`. Ver [certificados/README.md](certificados/README.md) para
agregar otro prestador.

Por defecto la revocación se comprueba en modo tolerante, sin red. `--revocacion`
la exige en línea (OCSP/CRL).

**Esto no reemplaza al validador oficial**: no dictamina sobre la validez legal.
El oficial paraguayo es el *Validador PY* del MIC, al que se llega desde
`acraiz.gov.py` → *Lista de confianza* → *Validador Nacional* (al 2026-09-18 esa
página devuelve 404). Por el Acuerdo de Reconocimiento Mutuo del Mercosur también
sirve el argentino, que acepta certificados paraguayos:
**https://validadordefirmas.gob.ar**

## Formato de la firma

`adbe.pkcs7.detached` + SHA-256, sin sello de tiempo. El bloqueo es
`/TransformMethod /FieldMDP` con `/Action /All` — firma de **aprobación** con
bloqueo de campos, no una certificación DocMDP. Todo esto fue medido contra un
PDF firmado con Acrobat y replicado campo por campo:
[docs/formato-acrobat.md](docs/formato-acrobat.md).

## Calibrar la apariencia sin firmar

`tools/probar-sello.py` estampa el sello con el mismo estilo que `firmar-pdf`
pero **sin firmar**: no necesita el token ni gasta intentos de PIN. Después mide
sobre el PDF renderizado dónde cayó la tinta.

```
$ tools/probar-sello.py documento.pdf --caja 1:340,70,560,140
documento_sello.pdf
caja 220x70 pt en la pagina 1, alineacion abajo-izq, cuerpo 12 pt
margenes de la tinta: izq 2.5  der 9.4  arriba 31.0  abajo 1.4 pt
bloque de texto: 207.7 x 34.6 pt
```

Es la forma de verificar cualquier cambio en el sello. Necesita `mutool`
(`mupdf-tools`); no usa Pillow ni numpy.

## Estado

Probado con token **Bit4id TokenME EVO v2** (chip NXP SecID P71) y certificado
cualificado de la **ICPP** (Infraestructura de Clave Pública Paraguaya), en
Ubuntu 24.04. Debería andar con cualquier token PKCS#11; si lo probás con otro,
avisá cómo te fue.

**Verificado el 2026-09-18:** un PDF firmado con esta herramienta pasa el
validador oficial **argentino** ([validadordefirmas.gob.ar](https://validadordefirmas.gob.ar)),
que reconoce certificados paraguayos por el Acuerdo de Reconocimiento Mutuo del
Mercosur. Resultado: *"Documento Válido — No hubo problemas en las firmas"*, con
la firma marcada como **Válida**.

No se pudo probar contra el *Validador PY* del MIC porque la página desde la que
se accede devuelve 404 (ver más abajo). Si lo probás, avisá cómo te fue.

## Licencia

MIT — ver [LICENSE](LICENSE).
