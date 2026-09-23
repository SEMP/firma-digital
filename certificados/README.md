# Certificados de la ICPP (Paraguay)

Cadena de confianza para validar firmas emitidas bajo la Infraestructura de Clave
Pública del Paraguay. Son certificados **públicos**: se incluyen acá solo para que
`validar-pdf` funcione sin configuración previa.

| Archivo | Titular | Vence |
|---|---|---|
| `ac_raiz_paraguay.pem` | Autoridad Certificadora Raíz del Paraguay (MIC) | 2032-08-07 |
| `vit_efirma.pem` | VIT S.A. (eFirma) | 2031-08-23 |
| `code100.pem` | CODE100 S.A. | 2032-01-24 |
| `documenta.pem` | CA-DOCUMENTA S.A. | 2032-03-28 |
| `ministerio_interior.pem` | Ministerio del Interior | 2032-03-31 |
| `sos_tecnologia.pem` | SOS TECNOLOGIA Y GESTION DE INFORMACION LTDA | 2032-05-26 |
| `confirma.pem` | CONFIRMA S.A. | 2032-05-29 |
| `itti.pem` | ITTI SAECA | 2032-06-26 |

Son **los siete prestadores cualificados acreditados** al 2026-09-23, más la raíz.
Con esto se valida cualquier firma emitida bajo la ICPP sin configurar nada.

## De dónde salen

```
https://www.acraiz.gov.py/adjunt/ac_raiz_py_sha256.crt
https://www.acraiz.gov.py/adjunt/Certificados/<nombre>.crt
```

Los certificados vienen en **DER** y hay que convertirlos a PEM. Ojo que algunos
prestadores publican dos: el viejo y el vigente (`ca-code100.crt` venció en 2025,
el bueno es `CODE100-2023.crt`). Verificar siempre la fecha:

```bash
openssl x509 -in certificado.pem -noout -subject -enddate
```

La lista completa de prestadores cualificados está en
`https://www.acraiz.gov.py/html/Certif_1PrestaServ.html`, con un enlace al
certificado de cada uno. La versión legible por máquina es la TSL:
`https://www.acraiz.gov.py/tsl/tsl_Py.xml`.

> El menú del sitio tiene la pestaña *Lista de confianza* rota (404 al 2026-09-18),
> pero los archivos son alcanzables por URL directa.

## Agregar el certificado de otro prestador

Bajá el `.crt` (viene en DER), convertilo y dejalo en esta carpeta:

```bash
openssl x509 -inform der -in "OTRO.crt" -out certificados/otro.pem
```

`validar-pdf` toma todos los `.pem` de acá, más los de
`~/.config/firma-digital/ca/`, más los que le pases con `--ca`.

## Refrescar

Estos certificados se renuevan cada varios años. Si aparece un error de cadena con
un certificado nuevo, volvé a bajarlos de las URL de arriba.
