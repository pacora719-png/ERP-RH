# ERP genérico en Streamlit

App de gestión (ERP ligero) adaptable a cualquier empresa. Incluye los módulos:

- ⚙️ **Configuración** — nombre de la empresa y ubicaciones/sedes
- 👥 **Empleados** — expedientes del personal
- ⏱️ **Horas y Nómina** — registro de horas, extras, bonificaciones y deducciones
- 📅 **Asistencia** — vacaciones, permisos e incapacidades
- 📦 **Inventario** — productos, stock y movimientos
- 📊 **Reportes** — resumen general

## Estructura de archivos

```
erp_app/
├── app.py                     # Página principal + login
├── database.py                # Conexión y esquema de la base de datos (SQLite)
├── requirements.txt
├── secrets.toml.ejemplo       # Plantilla de usuarios/contraseñas
└── pages/
    ├── 1_Configuracion.py
    ├── 2_Empleados.py
    ├── 3_Horas_y_Nomina.py
    ├── 4_Asistencia.py
    ├── 5_Inventario.py
    └── 6_Reportes.py
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

## Cómo desplegarlo en Streamlit Cloud

1. Sube esta carpeta a un repositorio de GitHub.
2. Entra a [streamlit.io/cloud](https://streamlit.io/cloud) y conecta el repositorio, señalando `app.py` como archivo principal.
3. En **Settings > Secrets**, pega el contenido de `secrets.toml.ejemplo` (con tu usuario y contraseña reales).
4. Al desplegar, ve primero al módulo **Configuración** para poner el nombre de tu empresa y crear tus ubicaciones/sedes — el resto de los módulos las usan.

## Primer uso

El orden recomendado la primera vez que abras la app:

1. **Configuración** → pon el nombre de tu empresa y crea al menos una ubicación/sede.
2. **Empleados** → agrega tu personal.
3. Ya puedes usar **Horas y Nómina**, **Asistencia** e **Inventario** con normalidad.

## Notas técnicas

- La base de datos es SQLite (`erp.db`), se crea automáticamente al primer arranque.
- En Streamlit Cloud el almacenamiento no es 100% persistente entre reinicios del contenedor;
  para uso en producción a largo plazo se recomienda migrar a una base de datos externa
  (por ejemplo PostgreSQL) cuando el negocio crezca.
