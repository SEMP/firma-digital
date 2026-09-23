# El formato que produce Acrobat

Todo lo de acá fue **medido** sobre un PDF firmado con Adobe Acrobat en Windows
con el mismo token, y replicado hasta que los campos coincidieron. No es lo que
dice la documentación: es lo que hace la herramienta.

## Parámetros de la firma

```
$ pdfsig documento_firmado_con_acrobat.pdf
  - Signing Hash Algorithm: SHA-256
  - Signature Type: adbe.pkcs7.detached
  - Total document signed
  - Signature Validation: Signature is Valid.
```

| Parámetro | Valor |
|---|---|
| SubFilter | `adbe.pkcs7.detached` |
| Digest | SHA-256 |
| Sello de tiempo | ninguno |
| Cadena embebida | solo el certificado final |

**`adbe.pkcs7.detached`, no PAdES.** Es contraintuitivo: PAdES
(`ETSI.CAdES.detached`) es el estándar europeo "correcto" para firma avanzada, y
es tentador asumir que es lo que hay que generar. Acrobat usa el otro, y los
validadores están calibrados contra Acrobat. Por eso el default de esta
herramienta es `adbe.pkcs7.detached` — que además es el default de pyHanko y de
`pdfsig`, así que no hay que hacer nada especial.

**Sin TSA.** Si tu proveedor sí usa sello de tiempo, el `pdfsig` de un documento
suyo lo va a mostrar y habrá que agregarlo (pyHanko lo soporta).

## "Bloquear el documento tras la firma"

Es la casilla que Acrobat ofrece al firmar. Produce esto:

```
/TransformMethod /FieldMDP
/TransformParams << /Action /All  /Type /TransformParams  /V /1.2  /P 1 >>
```

Lo importante: es **FieldMDP**, no DocMDP. O sea que sigue siendo una firma de
**aprobación** normal que además bloquea todos los campos de formulario. En el
archivo **no aparecen** `/DocMDP` ni `/Perms`.

La distinción importa porque el flag intuitivo de pyHanko sería `--certify`, y
**sería incorrecto**: crea una firma de certificación, que es otra cosa (declara
al firmante como autor del documento y restringe qué cambios se admiten después).

En la API de pyHanko el equivalente correcto es:

```python
fields.SigFieldSpec(
    sig_field_name="Firma1",
    field_mdp_spec=fields.FieldMDPSpec(fields.FieldMDPAction.ALL),   # /Action /All
    doc_mdp_update_value=fields.MDPPerm.NO_CHANGES,                  # /P 1
)
```

Además hay que pasar `docmdp_permissions=MDPPerm.NO_CHANGES` en el
`PdfSignatureMetadata`: sin eso pyHanko pide `FILL_FORMS` por defecto, choca con
el spec del campo y emite una advertencia (usa el valor correcto igual, pero el
mensaje confunde).

### El bloqueo excluye las firmas posteriores

`/Action /All` bloquea **todos** los campos de formulario, y un campo de firma es
uno de ellos. Verificado agregando una segunda firma a las dos variantes del
mismo documento:

| Primera firma | `docmdp_ok` de la primera | `modification_level` |
|---|---|---|
| con bloqueo | `False` | `OTHER` |
| sin bloqueo | `True` | `FORM_FILLING` |

En el caso bloqueado pyHanko informa *"Update of Reference(...) is not allowed
because the form field Firma2 is locked"*.

Consecuencia práctica: en un circuito de varias firmas, sólo el último firmante
debe bloquear.

**Al validar**, dos cosas que confunden:

- `docmdp_ok` es `True` también cuando **no hay ningún bloqueo**. Para distinguir
  "el bloqueo se respetó" de "no había bloqueo" hay que mirar si la firma declara
  un `/Reference` con `/TransformMethod /FieldMDP`.
- Las firmas que no son la última cubren `ENTIRE_REVISION`, no `ENTIRE_FILE`. Es
  lo normal en un documento multi-firma; exigirles `ENTIRE_FILE` marca como
  sospechoso un documento legítimo.

## El sello visible

Acrobat dibuja el nombre en grande a la izquierda, su logotipo de fondo, y a la
derecha tres líneas:

```
Firmado digitalmente por
NOMBRE COMPLETO DEL FIRMANTE
Fecha: 2026.09.18 11:49:07 -03'00'
```

Esta herramienta reproduce el bloque de texto, en Helvetica y sin recuadro. **No
reproduce el logotipo de Adobe** — es marca registrada de Adobe y no corresponde
en un documento firmado con otra herramienta — ni el nombre repetido en grande.

Detalles de pyHanko que cuesta descubrir:

- Solo `%(ts)s` se interpola solo. **`%(signer)s` hay que pasarlo** en
  `appearance_text_params`; se saca de `signer.signing_cert.subject.native`.
- El estilo va en `PdfSigner(..., stamp_style=...)`. El atajo
  `signers.sign_pdf()` **no acepta estilo**: hay que instanciar `PdfSigner`.
- Defaults que conviene pisar: la fuente es **Courier**
  (`SimpleFontEngineFactory` solo trae métricas de Courier; Helvetica se
  referencia sin metadata por ser una de las 14 fuentes estándar de PDF) y
  `border_width=3`, que dibuja un recuadro que Acrobat no pone.
- **`inner_content_layout` vs `box_layout_rule`**: el primero (en
  `TextStampStyle`) ubica el bloque **dentro del recuadro del sello**; el
  segundo (en `TextBoxStyle`) solo acomoda el texto dentro de su propia caja.
  Poner la alineación en el segundo no tiene efecto visible sobre dónde cae el
  sello: queda el default, centrado en ambos ejes.
- **El interlineado por defecto es igual al cuerpo** (`TextStyle.leading` en
  `None` ⇒ se usa `font_size`). Conviene fijarlo explícito si algo más —una
  previsualización, un cálculo de encaje— necesita predecir el alto del bloque.
- **`DEFAULT_TEXT_BOX_MARGIN` es 10 pt por lado**, que en un recuadro chico se
  come buena parte del ancho útil.
- **El ancho del texto se estima con un ratio plano**: `SimpleFontEngine.shape()`
  calcula `len(texto) * avg_width`, sin mirar las métricas reales por carácter.
  Con `avg_width=0.5` una línea en mayúsculas —un nombre completo, justamente—
  se subestima cerca de un 40% y el sobrante **se recorta** contra el borde del
  recuadro. En Helvetica las mayúsculas ocupan ~0.70 em. Esta herramienta usa
  0.70 y además calcula el cuerpo de letra que entra en la caja elegida
  (`cuerpo_que_entra()`), midiendo cada línea por tipo de carácter.

## Cómo inspeccionar un PDF firmado

```bash
pdfsig documento.pdf                    # parámetros de la firma

# estructura del bloqueo (los objetos suelen venir comprimidos)
mutool clean -d documento.pdf /tmp/insp.pdf
grep -a -A6 TransformMethod /tmp/insp.pdf

# cadena de certificados embebida en la firma
pdfsig -dump documento.pdf              # deja documento.pdf.sig0
openssl pkcs7 -inform der -in documento.pdf.sig0 -print_certs -noout

# dónde cayó el sello visible
mutool draw -r 150 -o /tmp/pag1.png documento.pdf 1
```
