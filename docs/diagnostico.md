# Diagnóstico

## Por qué NSS no sirve para firmar con estos tokens

Los certificados cualificados de firma suelen traer la clave privada marcada con
`CKA_ALWAYS_AUTHENTICATE`:

```
$ pkcs11-tool --module /usr/lib/bit4id/libbit4xpki.so -O -l
Private Key Object; RSA
  Access: always authenticate, sensitive, always sensitive, never extractable, local
```

Eso obliga, por estándar PKCS#11, a un **segundo login**
(`C_Login` con `CKU_CONTEXT_SPECIFIC`) inmediatamente antes de **cada**
operación de firma. `pkcs11-tool` lo implementa y se ve:

```
Logging in to "SecID XXXXXXXXXX".
Please enter User PIN:
Using signature algorithm SHA256-RSA-PKCS
Logging in to "SecID XXXXXXXXXX".
Please enter context specific PIN:      <-- este
```

**La capa NSS no lo implementa.** Los dos firmadores de Linux que pasan por NSS
leen el certificado sin problema y mueren exactamente en el paso de firmar:

| Herramienta | Síntoma |
|---|---|
| LibreOffice Draw (*Firmar PDF existente*) | Pide el primer PIN, lista el certificado, y al pulsar *Sign* **se cuelga**: `State: S`, `WCHAN: futex_do_wait`, cero sockets a `pcscd`, ~2% de CPU. No se destraba solo. `Force Quit` es seguro: nunca llegó a escribir. |
| `pdfsig` (poppler, backend NSS) | `-list-nicks` funciona; `-add-signature` falla con `signDocument: error getting signature info`. |

Okular también queda descartado: firma con el mismo backend NSS de poppler y,
empaquetado como snap, ni siquiera llega al lector.

pyHanko contra PKCS#11 **nativo** sí lo maneja, sin siquiera pedir el segundo PIN
por separado. De ahí el diseño de esta herramienta.

### Comprobar que el problema es ese y no el token

Si algo falla, primero verificá que el token firma. Esto no depende de ningún
PDF ni de NSS:

```bash
echo prueba > data.bin
pkcs11-tool --module /usr/lib/bit4id/libbit4xpki.so -l --sign \
    --id <ID-de-tu-clave> --mechanism SHA256-RSA-PKCS -i data.bin -o sig.bin

# verificar contra la clave publica del propio certificado
pkcs11-tool --module /usr/lib/bit4id/libbit4xpki.so --read-object \
    --type cert --id <ID> -o cert.der
openssl x509 -inform der -in cert.der -noout -pubkey > pub.pem
openssl dgst -sha256 -verify pub.pem -signature sig.bin data.bin   # Verified OK
```

Si eso da `Verified OK`, el token, el middleware y el PIN están bien: el problema
está más arriba.

## PDFs linealizados: la cobertura queda indeterminada

En un PDF **linealizado** ("vista web rápida"), el `startxref` final apunta a la
tabla de referencias del principio del archivo. La comprobación de cobertura de
pyHanko espera otro valor, así que no logra identificar la revisión firmada; al
no poder hacerlo **salta el análisis de diferencias** y devuelve
`ModificationLevel.OTHER` por defecto.

Eso **no significa que el documento esté adulterado**: significa que no se pudo
analizar. Se nota cuando se agrega una segunda firma a un documento linealizado
firmado por otra persona — la primera firma pasa de `ENTIRE_FILE` a
`CONTIGUOUS_BLOCK_FROM_START` / `OTHER` sin que nada se haya roto.

`validar-pdf` detecta el caso (busca `/Linearized` en los primeros 2 KB) y lo
informa como indeterminado en vez de como falla.

Para verlo a mano:

```bash
python -c "
from pyhanko.pdf_utils.reader import PdfFileReader
r = PdfFileReader(open('doc.pdf','rb')); e = r.embedded_signatures[0]
br = [int(v) for v in e.sig_object.get_object()['/ByteRange']]
print(open('doc.pdf','rb').read()[:br[2]+br[3]][-40:])
print('esperado:', r.xrefs.get_startxref_for_revision(e.signed_revision))"
```

Si el `startxref` que aparece al final de la zona firmada no coincide con el
esperado, es este caso.

## Errores frecuentes

**`Could not find private key with label 'X'`** — las etiquetas de los tres
objetos suelen ser distintas entre sí (`DS3`, `DS3_Private`, `DS3_Public` en los
Bit4id). Mirá las reales con `pkcs11-tool -O -l`. Normalmente conviene **no**
configurar ninguna y dejar que se autodetecten.

**`pkcs11 ... [unavailable]` en pyHanko** — falta el extra, que pertenece a
`pyhanko` y no a `pyhanko-cli`: `pipx inject pyhanko-cli 'pyhanko[pkcs11]'`.

**`No apps associated with package pyhanko`** — la CLI está en `pyhanko-cli`.

**`Certificate issuer is unknown` al validar** — falta la cadena de la CA en el
almacén local. **No afecta la validez de la firma**, y aparece igual en los PDF
firmados con Acrobat. Para resolverlo hay que conseguir los certificados raíz e
intermedio del prestador y agregarlos al almacén de confianza.

**`Generic processing error`** — pyHanko oculta la traza. Corré con `--verbose`
**antes** del subcomando:
`pyhanko --verbose sign addsig ...`

## Sacar el token del USB

Se saca directamente, sin "extraer con seguridad". Es un dispositivo **CCID**, no
almacenamiento USB: no hay filesystem montado ni caché de escritura pendiente —
por eso tampoco aparece en el gestor de archivos. La única precaución real es no
sacarlo **durante** una firma o un cambio de PIN, porque ahí sí hay escritura en
el chip.
