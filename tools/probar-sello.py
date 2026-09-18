#!/usr/bin/env python3
"""Estampa el sello SIN firmar y mide donde cayo la tinta.

Sirve para calibrar la apariencia (cuerpo de letra, margenes, alineacion) sin
gastar intentos de PIN y sin tener el token conectado: usa exactamente el mismo
estilo que arma `firmar-pdf`, pero aplicando el sello como contenido normal en
vez de como apariencia de una firma.

    tools/probar-sello.py documento.pdf --caja 1:340,70,560,140

Imprime el cuerpo de letra elegido y los margenes reales de la tinta dentro del
recuadro pedido, medidos sobre el PDF renderizado. Necesita `mutool`
(paquete mupdf-tools); no requiere Pillow ni numpy.
"""
import argparse
import importlib.util
import pathlib
import subprocess
import sys
import tempfile

from pyhanko.pdf_utils import layout, text as pdftext
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.layout import BoxConstraints
from pyhanko.stamp import TextStampStyle

AQUI = pathlib.Path(__file__).resolve().parent


def cargar_firmador():
    """Importa firmar-pdf como modulo (el guion impide un import normal)."""
    ruta = AQUI.parent / "firmar-pdf"
    spec = importlib.util.spec_from_loader("firmador", None)
    mod = importlib.util.module_from_spec(spec)
    codigo = ruta.read_text().replace("sys.exit(main())", "pass")
    exec(compile(codigo, str(ruta), "exec"), mod.__dict__)
    return mod


def leer_pgm(ruta):
    """(ancho, alto, pixeles) de un PGM binario P5, sin dependencias."""
    datos = pathlib.Path(ruta).read_bytes()
    campos, pos = [], 2
    while len(campos) < 3:
        while datos[pos:pos + 1].isspace():
            pos += 1
        if datos[pos:pos + 1] == b"#":
            while datos[pos:pos + 1] not in (b"\n", b""):
                pos += 1
            continue
        ini = pos
        while not datos[pos:pos + 1].isspace():
            pos += 1
        campos.append(int(datos[ini:pos]))
    return campos[0], campos[1], datos[pos + 1:]


def medir_tinta(pdf, pagina, caja, dpi=200):
    """Margenes (izq, der, arriba, abajo) de la tinta dentro de la caja, en pt."""
    tmp = tempfile.mkdtemp(prefix="probar-sello-")
    pgm = f"{tmp}/p.pgm"
    subprocess.run(["mutool", "draw", "-r", str(dpi), "-F", "pgm", "-o", pgm,
                    pdf, str(pagina)], check=True, capture_output=True)
    ancho, alto, px = leer_pgm(pgm)
    e = dpi / 72.0
    x1, y1, x2, y2 = caja
    cx0, cx1 = int(x1 * e), min(ancho, int(x2 * e))
    cy0, cy1 = max(0, int(alto - y2 * e)), min(alto, int(alto - y1 * e))

    min_x = min_y = 10 ** 9
    max_x = max_y = -1
    for y in range(cy0, cy1):
        fila = px[y * ancho + cx0: y * ancho + cx1]
        for x, v in enumerate(fila):
            if v < 200:
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y - cy0), max(max_y, y - cy0)
    if max_x < 0:
        return None
    return (min_x / e, (cx1 - cx0 - 1 - max_x) / e,
            min_y / e, (cy1 - cy0 - 1 - max_y) / e,
            (max_x - min_x) / e, (max_y - min_y) / e)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("entrada", help="PDF sobre el que estampar")
    p.add_argument("--caja", required=True, metavar="P:X1,Y1,X2,Y2")
    p.add_argument("--alineacion", default="abajo-izq")
    p.add_argument("--nombre", default="NOMBRE DE PRUEBA DEL FIRMANTE",
                   help="texto a usar como firmante (no hace falta el token)")
    p.add_argument("--tamano-fuente", type=int, default=None)
    p.add_argument("--salida", default=None, help="default: <entrada>_sello.pdf")
    p.add_argument("--dpi", type=int, default=200)
    a = p.parse_args()

    m = cargar_firmador()
    pagina, caja = m.parse_caja(a.caja)
    x1, y1, x2, y2 = caja
    ancho, alto = x2 - x1, y2 - y1
    lineas = m.lineas_del_sello(a.nombre)
    cuerpo = a.tamano_fuente or m.cuerpo_que_entra(lineas, ancho, alto)

    estilo = TextStampStyle(
        stamp_text=m.TEXTO_SELLO, timestamp_format=m.FORMATO_FECHA,
        inner_content_layout=m.regla_de_caja(a.alineacion),
        text_box_style=pdftext.TextBoxStyle(
            font=m.fuente(lineas), font_size=cuerpo,
            leading=int(round(cuerpo * m.INTERLINEA)),
            box_layout_rule=layout.SimpleBoxLayoutRule(
                x_align=layout.AxisAlignment.ALIGN_MIN,
                y_align=layout.AxisAlignment.ALIGN_MIN,
                margins=layout.Margins.uniform(0)),
        ),
        border_width=0, background=None,
    )

    salida = a.salida or str(
        pathlib.Path(a.entrada).with_name(
            pathlib.Path(a.entrada).stem + "_sello.pdf"))
    with open(a.entrada, "rb") as fh:
        w = IncrementalPdfFileWriter(fh)
        sello = estilo.create_stamp(
            w, BoxConstraints(width=ancho, height=alto), {"signer": a.nombre})
        sello.apply(pagina - 1, x1, y1)
        with open(salida, "wb") as out:
            w.write(out)

    print(f"{salida}")
    print(f"caja {ancho}x{alto} pt en la pagina {pagina}, "
          f"alineacion {a.alineacion}, cuerpo {cuerpo} pt")
    med = medir_tinta(salida, pagina, caja, a.dpi)
    if med is None:
        print("no se detecto tinta dentro de la caja")
        return 1
    izq, der, arr, aba, bw, bh = med
    print(f"margenes de la tinta: izq {izq:.1f}  der {der:.1f}  "
          f"arriba {arr:.1f}  abajo {aba:.1f} pt")
    print(f"bloque de texto: {bw:.1f} x {bh:.1f} pt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
