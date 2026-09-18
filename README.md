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

# el firmador
sudo install -m755 firmar-pdf /usr/local/bin/firmar-pdf
```

## Uso

```bash
firmar-pdf doc.pdf firmado.pdf                          # selector visual (default)
firmar-pdf doc.pdf firmado.pdf --caja 1:340,70,560,140  # sin ventana, para lotes
firmar-pdf doc.pdf firmado.pdf --invisible              # sin sello visible
firmar-pdf doc.pdf firmado.pdf --sin-bloqueo            # sin bloquear los campos
```

En el selector: arrastrás el área, `<` `>` cambian de página, `+` `−` y *Ajustar*
controlan el zoom, la rueda del mouse hace scroll. **Enter** firma, **Escape**
cancela. Al confirmar imprime el `--caja` equivalente, para reusarlo en lote.

`--caja` usa **puntos PDF con origen abajo-izquierda** (A4 = 595×842).

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

## Formato de la firma

`adbe.pkcs7.detached` + SHA-256, sin sello de tiempo. El bloqueo es
`/TransformMethod /FieldMDP` con `/Action /All` — firma de **aprobación** con
bloqueo de campos, no una certificación DocMDP. Todo esto fue medido contra un
PDF firmado con Acrobat y replicado campo por campo:
[docs/formato-acrobat.md](docs/formato-acrobat.md).

## Estado

Probado con token **Bit4id TokenME EVO v2** (chip NXP SecID P71) y certificado
cualificado de la **ICPP** (Infraestructura de Clave Pública Paraguaya), en
Ubuntu 24.04. Debería andar con cualquier token PKCS#11; si lo probás con otro,
avisá cómo te fue.

**No verificado:** que los validadores oficiales acepten los PDF firmados con
esta herramienta. Los parámetros son idénticos a los de Acrobat, pero conviene
que valides un documento de prueba antes de usarla para algo con consecuencias.

## Licencia

MIT — ver [LICENSE](LICENSE).
