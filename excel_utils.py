"""
Utilidades compartidas para exportar DataFrames a Excel
y leer plantillas de Excel para carga masiva.
"""
import io
import pandas as pd


def exportar_excel(df: pd.DataFrame, nombre_hoja: str = "Datos") -> bytes:
    """Convierte un DataFrame a bytes de un archivo .xlsx listo para descargar."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return buffer.getvalue()


def plantilla_empleados() -> bytes:
    """Genera una plantilla vacía (con encabezados y una fila de ejemplo) para cargar empleados."""
    columnas = [
        "nombre", "identificacion", "cargo", "ubicacion", "fecha_ingreso",
        "salario_base", "valor_hora", "telefono", "eps", "fondo_pension",
        "arl", "caja_compensacion"
    ]
    fila_ejemplo = [
        "Juan Pérez", "1234567890", "Mesero", "Sede Principal", "2026-01-15",
        1300000, 6000, "3001234567", "Sura EPS", "Porvenir", "Sura ARL", "Comfama"
    ]
    df = pd.DataFrame([fila_ejemplo], columns=columnas)
    return exportar_excel(df, "Empleados")
