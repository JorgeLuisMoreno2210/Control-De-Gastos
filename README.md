# Control de Gastos

Una aplicación sencilla para anotar tus gastos, ponerles un presupuesto por categoría y ver en qué se va tu dinero cada mes.

- Funciona en tu navegador, pero **todo corre en tu computador**: tus datos no salen de él.
- **No necesitas instalar nada** aparte de Python 3.9 o superior.

## Cómo usarla

1. Abre una terminal en esta carpeta.
2. Ejecuta:

   ```
   python main.py
   ```

3. Se abrirá el navegador en `http://127.0.0.1:8000`. Si no se abre, copia esa dirección.
4. Para cerrar, vuelve a la terminal y presiona `Ctrl + C`.

Si el puerto está ocupado: `python main.py --puerto 8001`.

## Qué puedes hacer

- **Anotar gastos** con fecha, monto, categoría y una descripción opcional.
- **Fijar un presupuesto** para cada categoría. La barra cambia de color: verde (vas bien), naranja (cerca del límite, desde el 80 %) y rojo (te pasaste).
- **Cambiar de mes** para revisar meses anteriores.
- **Descargar** los gastos del mes en un archivo CSV que abre Excel.
- **Eliminar** gastos anotados por error.

## Opciones

| Opción | Para qué sirve |
| --- | --- |
| `--puerto 9000` | Usar otro puerto |
| `--db mis_gastos.db` | Guardar los datos en otro archivo |
| `--no-abrir` | No abrir el navegador automáticamente |

Tus datos quedan en el archivo `gastos.db`. Para hacer una copia de seguridad, cópialo.

## Pruebas

```
python -m unittest discover -s tests -v
```

## Cómo está organizado

```
main.py              Arranca la aplicación
gastos/db.py         Base de datos SQLite
gastos/servicio.py   Reglas: validaciones, presupuestos, resumen, CSV
gastos/servidor.py   Servidor local y API JSON
gastos/static/       Pantalla de la aplicación
tests/               Pruebas automáticas
```

Decisiones de diseño:

- **Dinero en centavos enteros**, para que sumas como 0,10 + 0,20 siempre den exactos.
- **Consultas parametrizadas** en SQL y texto escapado en pantalla, contra inyecciones.
- **El servidor solo escucha en tu equipo** (`127.0.0.1`), no en la red.
- **El CSV neutraliza fórmulas** (`=`, `+`, `-`, `@`) para que no se ejecuten al abrirlo en Excel.
- **Sin dependencias externas**: solo la biblioteca estándar de Python.
