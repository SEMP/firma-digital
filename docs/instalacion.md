# Instalación

Probado en Ubuntu 24.04. Los pasos 1 y 2 dependen de tu token; el 3 y el 4 son
iguales para todos.

## 1. Middleware del token

Instalá el middleware que provea tu proveedor. Para Bit4id:

```bash
sudo apt install ./Bit4id_Middleware.deb   # el ./ es obligatorio
```

**Con `apt`, no con `dpkg -i`.** `dpkg` no resuelve dependencias: si falta alguna
(`pcscd`, `libpcsclite1`, `libccid`) el paquete queda en estado roto y hay que
correr `sudo apt install -f` después. `apt` las baja antes de instalar.

El módulo PKCS#11 queda, para Bit4id, en `/usr/lib/bit4id/libbit4xpki.so`.
Confirmalo con:

```bash
dpkg -L libbit4xpki | grep '\.so$'
```

## 2. Verificar que el token responde

```bash
sudo apt install pcsc-tools opensc
pcsc_scan                    # Ctrl+C para salir: es un monitor, no termina solo
pkcs11-tool --module /usr/lib/bit4id/libbit4xpki.so -O -l
```

El primero debe listar tu lector con `Card inserted`. El segundo, tras pedir el
PIN, debe mostrar la clave privada, la pública y el certificado. Anotá las
etiquetas (`label:`) por si después necesitás configurarlas a mano.

### `pcscd` aparece inactivo y está bien

En Ubuntu 24.04 `pcscd` se activa **por socket** (`pcscd.socket`, con
`--auto-exit`): arranca cuando un programa pide el lector y se apaga tras un
minuto sin uso. **No** hagas `systemctl enable pcscd.service`.

### Cuidado con los intentos de PIN

Estos tokens se bloquean a los 3 PIN incorrectos y desbloquear requiere el PUK.
Para ver cuántos intentos quedan **sin gastar ninguno** (no requiere login):

```bash
pkcs11-tool --module /usr/lib/bit4id/libbit4xpki.so -T | grep flags
```

- `user PIN count low` → ya hubo fallos, quedan pocos.
- `user PIN final try` → **no reintentar**, pedir el PUK al proveedor.

Un login exitoso resetea el contador. Si el PIN lo generó un gestor de
contraseñas, **pegalo, no lo tipees**: `l` minúscula y `1` se confunden en muchas
tipografías.

## 3. Dependencias

```bash
sudo apt install pipx python3-tk mupdf-tools
pipx install 'pyhanko-cli[pkcs11]'
pipx inject pyhanko-cli 'pyhanko[pkcs11]'
```

Tres detalles que hacen perder tiempo:

- La CLI de pyHanko vive en el paquete **`pyhanko-cli`**, no en `pyhanko`. Un
  `pipx install pyhanko` responde *"No apps associated with package"*.
- El extra `[pkcs11]` pertenece a **`pyhanko`**, no a `pyhanko-cli`. Sin el
  `pipx inject`, el subcomando aparece como `pkcs11 ... [unavailable]`.
- `python3-tk` es para el selector visual y `mupdf-tools` aporta `mutool`, que
  renderiza las páginas. Sin ellos, `--caja` o `--invisible` igual funcionan.

## 4. Instalar el firmador

```bash
sudo install -m755 firmar-pdf /usr/local/bin/firmar-pdf
```

Si lo instalás en `~/.local/bin`, asegurate de que esté en el `PATH`.

El script arranca con `#!/usr/bin/env python3`, así que necesita que el Python
del sistema vea pyHanko. Si lo instalaste con `pipx` (que lo aísla en su propio
entorno), apuntá el shebang al intérprete del venv:

```bash
sed -i "1s|.*|#!$(pipx environment --value PIPX_LOCAL_VENVS)/pyhanko-cli/bin/python|" \
    /usr/local/bin/firmar-pdf
```

## Verificar la instalación

```bash
firmar-pdf --help
echo "prueba" > /tmp/t.txt && libreoffice --headless --convert-to pdf --outdir /tmp /tmp/t.txt
firmar-pdf /tmp/t.pdf /tmp/t-firmado.pdf
pdfsig /tmp/t-firmado.pdf          # debe decir "Signature is Valid"
```
