"""
Utilidades compartidas para exportar DataFrames a Excel,
leer plantillas de Excel para carga masiva, y generar PDFs
de liquidación de nómina.
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
        "salario_base", "telefono", "eps", "fondo_pension",
        "arl", "caja_compensacion"
    ]
    fila_ejemplo = [
        "Juan Pérez", "1234567890", "Mesero", "Sede Principal", "2026-01-15",
        1300000, "3001234567", "Sura EPS", "Porvenir", "Sura ARL", "Comfama"
    ]
    df = pd.DataFrame([fila_ejemplo], columns=columnas)
    return exportar_excel(df, "Empleados")


def plantilla_horas() -> bytes:
    """Genera una plantilla vacía para cargar horas de varios empleados a la vez.
    Se identifica al empleado por su número de identificación."""
    columnas = [
        "identificacion_empleado", "fecha", "hora_entrada", "hora_salida",
        "horas_extra_diurna", "horas_extra_nocturna", "horas_extra_dominical_festivo",
        "horas_extra_dominical_festivo_nocturna", "horas_recargo_nocturno", "horas_recargo_dominical",
        "horas_descuento", "tipo_descuento", "bonificacion", "deduccion", "observacion"
    ]
    fila_ejemplo = [
        "1234567890", "2026-07-01", "08:00", "17:00",
        2, 0, 0, 0, 0, 0, 1, "Alimentación", 0, 0, ""
    ]
    df = pd.DataFrame([fila_ejemplo], columns=columnas)
    return exportar_excel(df, "Horas")
    """
    Genera un PDF de liquidación de nómina para un empleado en un período.
    `datos` debe incluir: empresa (dict con nombre, nit, representante),
    empleado (dict con nombre, identificacion, cargo), periodo (desde, hasta),
    conceptos (lista de tuplas (nombre, valor)), total.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=14, spaceAfter=4)
    normal = styles["Normal"]

    elementos = []

    empresa = datos.get("empresa", {})
    elementos.append(Paragraph(empresa.get("nombre", "Mi Empresa"), titulo_style))
    if empresa.get("nit"):
        elementos.append(Paragraph(f"NIT: {empresa['nit']}", normal))
    if empresa.get("representante"):
        elementos.append(Paragraph(f"Representante legal: {empresa['representante']}", normal))
    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(Paragraph("Comprobante de Liquidación de Nómina", styles["Heading2"]))
    elementos.append(Spacer(1, 0.3 * cm))

    empleado = datos.get("empleado", {})
    periodo = datos.get("periodo", {})
    info_data = [
        ["Empleado:", empleado.get("nombre", "")],
        ["Identificación:", empleado.get("identificacion", "")],
        ["Cargo:", empleado.get("cargo", "")],
        ["Período:", f"{periodo.get('desde', '')} a {periodo.get('hasta', '')}"],
    ]
    tabla_info = Table(info_data, colWidths=[4 * cm, 10 * cm])
    tabla_info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla_info)
    elementos.append(Spacer(1, 0.5 * cm))

    conceptos = datos.get("conceptos", [])
    tabla_data = [["Concepto", "Valor"]] + [[c[0], f"${c[1]:,.0f}"] for c in conceptos]
    tabla_data.append(["TOTAL A PAGAR", f"${datos.get('total', 0):,.0f}"])

    tabla_conceptos = Table(tabla_data, colWidths=[10 * cm, 4 * cm])
    tabla_conceptos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_conceptos)

    doc.build(elementos)
    return buffer.getvalue()
