# ERP genérico en Streamlit

App de gestión de nómina y personal (ERP ligero), adaptable a cualquier empresa. Incluye los módulos:

- ⚙️ **Configuración** — datos de la empresa (nombre, NIT, representante legal, logo), ubicaciones/sedes y parámetros de nómina (horas mensuales, recargos, salud/pensión, auxilio de transporte)
- 👥 **Empleados** — expedientes del personal, afiliaciones (EPS, pensión, ARL, caja de compensación), carga/descarga masiva en Excel
- ⏱️ **Horas y Nómina** — registro de horas, horas extra (diurna, nocturna, dominical/festivo, dominical/festivo nocturna), recargos (nocturno, dominical), tiempo a descontar, reporte por período para todos los empleados y sedes, y carga masiva desde Excel
- 📅 **Asistencia** — vacaciones, permisos e incapacidades
- 📄 **Cancelaciones de contrato** — retiros, motivo, valor de liquidación e indemnización, archivo de evidencia, lista de empleados retirados
- 🧾 **Liquidador de Nómina** — toma las horas ya registradas en un período y genera la colilla de pago en PDF
- 📊 **Reportes** — nómina liquidada, liquidaciones e indemnizaciones por retiro, novedades de asistencia

## Estructura de archivos

```
erp_app/
├── app.py                       # Página principal + login
├── database.py                  # Conexión y esquema de la base de datos (SQLite o PostgreSQL)
├── excel_utils.py                # Exportar/importar Excel y generar PDF de liquidación
├── requirements.txt
├── secrets.toml.ejemplo         # Plantilla de usuarios/contraseñas y base de datos
└── pages/
    ├── 1_Configuracion.py
    ├── 2_Empleados.py
    ├── 3_Horas_y_Nomina.py
    ├── 4_Asistencia.py
    ├── 5_Cancelaciones.py
    ├── 6_Liquidador_Nomina.py
    └── 7_Reportes.py
```

## Cómo correrlo localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo configurar el usuario y contraseña

1. Crea una carpeta `.streamlit/` junto a `app.py`.
2. Copia `secrets.toml.ejemplo` dentro de esa carpeta y renómbralo a `secrets.toml`.
3. Cambia el usuario y la contraseña de ejemplo.

## Cómo conectar PostgreSQL (recomendado en producción)

Por defecto la app usa SQLite (un archivo local). Para que tus datos no dependan del
almacenamiento efímero de Streamlit Cloud, puedes conectar una base de datos PostgreSQL
externa (por ejemplo en [Neon](https://neon.com), que tiene un plan gratis sin tarjeta):

1. Crea una cuenta y un proyecto en Neon (u otro proveedor de PostgreSQL).
2. Copia la cadena de conexión que te dan, algo como:
   `postgresql://usuario:clave@host/dbname?sslmode=require`
3. En Streamlit Cloud → Settings → Secrets, agrega:
   ```
   database_url = "postgresql://usuario:clave@host/dbname?sslmode=require"
   ```
4. Reinicia la app (menú ⋮ → Reboot app). La app detecta automáticamente que hay una
   base de datos configurada y crea las tablas ahí en el primer arranque — no necesitas
   tocar nada más del código.

Si más adelante quitas `database_url` de los Secrets, la app vuelve a usar SQLite local
sin problema (pero los datos no se migran solos entre un motor y otro).

## Cómo desplegarlo en Streamlit Cloud

1. Sube esta carpeta a un repositorio de GitHub (todos los archivos, incluida la carpeta `pages/`).
2. Entra a [streamlit.io/cloud](https://streamlit.io/cloud) y conecta el repositorio, señalando `app.py` como archivo principal.
3. En **Settings > Secrets**, pega el contenido de `secrets.toml.ejemplo` (con tu usuario, contraseña y, si aplica, tu `database_url` reales).
4. Reinicia la app (menú ⋮ → Reboot app) después de cualquier cambio en el repositorio o en los Secrets.

## Primer uso

El orden recomendado la primera vez que abras la app:

1. **Configuración** → pon el nombre de tu empresa, NIT, representante legal, logo, crea al menos una ubicación/sede, y revisa los parámetros de nómina (recargos, salud/pensión, auxilio de transporte).
2. **Empleados** → agrega tu personal (el valor hora se calcula automáticamente a partir del salario base), o cárgalos masivamente desde la pestaña de Excel.
3. **Horas y Nómina** → registra las horas trabajadas día a día, o cárgalas masivamente desde Excel. Desde la pestaña de Excel también puedes descargar el reporte de un período con todos los empleados y sedes.
4. **Liquidador de Nómina** → selecciona el período y el empleado, y descarga la colilla de pago en PDF.
5. **Cancelaciones de contrato** → cuando se retire un empleado, registra la liquidación/indemnización ahí.

## Notas técnicas

- Sin `database_url` configurada, la base de datos es SQLite (`erp.db`), se crea automáticamente al primer arranque, pero no es 100% persistente entre reinicios del contenedor en Streamlit Cloud.
- Con `database_url` configurada (PostgreSQL), los datos son completamente persistentes y sobreviven a reinicios y redespliegues.
- Los archivos de evidencia de cancelaciones se guardan dentro de la base de datos (no en el sistema de archivos), para que sobrevivan a reinicios del contenedor.
- Los multiplicadores de horas extra y recargos, así como el auxilio de transporte y los
  porcentajes de salud/pensión, son editables en **Configuración** porque cambian por decreto
  del gobierno colombiano cada año.
