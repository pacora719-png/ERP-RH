import streamlit as st
import pandas as pd
import base64
import io
import zipfile
from datetime import date
from database import get_connection, get_config, get_multiplicadores, get_parametros_nomina, execute, read_sql_query

st.set_page_config(page_title="Liquidador de Nómina", page_icon="🧾", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("🧾 Liquidador de Nómina")

# ---------- DATOS DE LA EMPRESA (desde Configuración) ----------
nombre_empresa = get_config("nombre_empresa", "Mi Empresa")
nit_empresa = get_config("nit_empresa", "")
representante_empresa = get_config("representante_empresa", "")
logo_base64 = get_config("logo_empresa_base64", "")

with st.expander("🏢 Datos de la empresa usados en el PDF (edítalos en Configuración)"):
    st.write(f"**Empresa:** {nombre_empresa}  |  **NIT:** {nit_empresa}  |  **Representante legal:** {representante_empresa}")

with get_connection() as conn:
    empleados_df = read_sql_query("SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn)

if empleados_df.empty:
    st.warning("No hay empleados activos. Ve a **Empleados** para agregar al menos uno.")
    st.stop()

m = get_multiplicadores()
p = get_parametros_nomina()


def pesos(valor):
    return "${:,.0f}".format(valor).replace(",", ".")


def calcular_liquidacion(emp_row, horas_periodo, dias, extras):
    """Calcula la liquidación de un empleado a partir de sus horas del período
    (ya sumadas en horas_periodo) y las opciones especiales (extras)."""
    salario_mensual = float(emp_row["salario_base"])
    valor_hora = float(emp_row["valor_hora"])

    salario = (salario_mensual / 30) * dias

    ed = valor_hora * m["extra_diurna"] * horas_periodo["horas_extra_diurna"]
    en = valor_hora * m["extra_nocturna"] * horas_periodo["horas_extra_nocturna"]
    ef = valor_hora * m["extra_dominical_festivo"] * horas_periodo["horas_extra_dominical_festivo"]
    end = valor_hora * m["extra_dominical_festivo_nocturna"] * horas_periodo["horas_extra_dominical_festivo_nocturna"]
    rn = valor_hora * m["recargo_nocturno"] * horas_periodo["horas_recargo_nocturno"]
    rd = valor_hora * m["recargo_dominical"] * horas_periodo["horas_recargo_dominical"]
    descuento_tiempo = valor_hora * horas_periodo["horas_descuento"]

    ibc = salario + ed + en + ef + end + rn + rd

    salud = 0 if extras["no_salud"] else ibc * p["salud_pct"]
    pension = 0 if extras["no_pension"] else ibc * p["pension_pct"]

    auxilio = 0
    if (salario_mensual <= p["tope_salarial_auxilio_transporte"]
            and not (extras["incapacidad"] or extras["maternidad"] or extras["sin_auxilio"])):
        auxilio = (p["auxilio_transporte_mensual"] / 30) * dias

    bonificaciones = horas_periodo["bonificacion"] + extras["bonificaciones_adicionales"]
    devengado = ibc + auxilio + bonificaciones

    deducciones = (salud + pension + descuento_tiempo + horas_periodo["deduccion"]
                   + extras["consumos"] + extras["danos"] + extras["ahorros"] + extras["otros"])
    neto = devengado - deducciones

    return {
        "salario": salario, "ed": ed, "en": en, "ef": ef, "end": end, "rn": rn, "rd": rd,
        "auxilio": auxilio, "bonificaciones": bonificaciones, "salud": salud, "pension": pension,
        "descuento_tiempo": descuento_tiempo, "deduccion_registrada": horas_periodo["deduccion"],
        "consumos": extras["consumos"], "danos": extras["danos"], "ahorros": extras["ahorros"],
        "otros": extras["otros"], "devengado": devengado, "deducciones": deducciones, "neto": neto,
    }


def generar_pdf(emp_row, periodo, dias, horas_periodo, calculo):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    if logo_base64:
        try:
            logo_bytes = base64.b64decode(logo_base64)
            from reportlab.lib.utils import ImageReader
            c.drawImage(ImageReader(io.BytesIO(logo_bytes)), 50, 720, width=100, height=50,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, 750, "COLILLA DE PAGO")

    y = 700
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Empresa: {nombre_empresa}"); y -= 15
    c.drawString(50, y, f"NIT: {nit_empresa}"); y -= 15
    c.drawString(50, y, f"Empleado: {emp_row['nombre']}"); y -= 15
    c.drawString(50, y, f"Identificación: {emp_row['identificacion'] or ''}"); y -= 15
    c.drawString(50, y, f"Período: {periodo[0].strftime('%d/%m/%Y')} al {periodo[1].strftime('%d/%m/%Y')}"); y -= 15
    c.drawString(50, y, f"Días trabajados: {dias}"); y -= 20

    c.setFont("Helvetica-Bold", 11); c.drawString(50, y, "DEVENGADOS"); y -= 15
    c.setFont("Helvetica", 10)
    for etiqueta, valor in [("Salario", calculo["salario"]), ("Auxilio de transporte", calculo["auxilio"]),
                             ("Bonificaciones", calculo["bonificaciones"])]:
        c.drawString(50, y, etiqueta); c.drawRightString(550, y, pesos(valor)); y -= 15
    y -= 5

    c.setFont("Helvetica-Bold", 11); c.drawString(50, y, "HORAS EXTRAS Y RECARGOS"); y -= 15
    c.setFont("Helvetica", 10)
    filas_horas = [
        (f"Extra diurna ({horas_periodo['horas_extra_diurna']}h)", calculo["ed"]),
        (f"Extra nocturna ({horas_periodo['horas_extra_nocturna']}h)", calculo["en"]),
        (f"Extra dominical/festivo ({horas_periodo['horas_extra_dominical_festivo']}h)", calculo["ef"]),
        (f"Extra dominical/festivo nocturna ({horas_periodo['horas_extra_dominical_festivo_nocturna']}h)", calculo["end"]),
        (f"Recargo nocturno ({horas_periodo['horas_recargo_nocturno']}h)", calculo["rn"]),
        (f"Recargo dominical ({horas_periodo['horas_recargo_dominical']}h)", calculo["rd"]),
    ]
    for etiqueta, valor in filas_horas:
        c.drawString(50, y, etiqueta); c.drawRightString(550, y, pesos(valor)); y -= 15
    y -= 5

    c.setFont("Helvetica-Bold", 11); c.drawString(50, y, "DEDUCCIONES"); y -= 15
    c.setFont("Helvetica", 10)
    filas_deducciones = [
        ("Salud", calculo["salud"]), ("Pensión", calculo["pension"]),
        (f"Tiempo no laboral ({horas_periodo['horas_descuento']}h)", calculo["descuento_tiempo"]),
        ("Deducciones registradas en horas", calculo["deduccion_registrada"]),
        ("Consumos", calculo["consumos"]), ("Daños", calculo["danos"]),
        ("Ahorros", calculo["ahorros"]), ("Otros", calculo["otros"]),
    ]
    for etiqueta, valor in filas_deducciones:
        c.drawString(50, y, etiqueta); c.drawRightString(550, y, pesos(valor)); y -= 15
    y -= 5

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "TOTAL DEVENGADO"); c.drawRightString(550, y, pesos(calculo["devengado"])); y -= 15
    c.drawString(50, y, "TOTAL DEDUCCIONES"); c.drawRightString(550, y, pesos(calculo["deducciones"])); y -= 15
    c.drawString(50, y, "NETO A PAGAR"); c.drawRightString(550, y, pesos(calculo["neto"])); y -= 40

    c.line(50, y, 250, y); c.drawString(50, y - 15, emp_row["nombre"])
    c.line(300, y, 550, y); c.drawString(300, y - 15, representante_empresa)

    c.save()
    return buffer.getvalue()


# ---------- PERÍODO Y EMPLEADO ----------
st.header("Período a liquidar")
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Inicio", date.today().replace(day=1))
with col2:
    fecha_fin = st.date_input("Fin", date.today())

st.header("Empleado")
empleado_id = st.selectbox(
    "Selecciona el empleado a liquidar",
    empleados_df["id"].tolist(),
    format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
)
emp_row = empleados_df[empleados_df["id"] == empleado_id].iloc[0]

with get_connection() as conn:
    horas_df = read_sql_query("""
        SELECT * FROM horas WHERE empleado_id=? AND fecha BETWEEN ? AND ?
    """, conn, params=(int(empleado_id), str(fecha_inicio), str(fecha_fin)))

if horas_df.empty:
    st.warning("Este empleado no tiene horas registradas en el período seleccionado. Ve a **Horas y Nómina** para registrarlas primero.")
else:
    dias_default = horas_df["fecha"].nunique()
    horas_periodo = {
        "horas_extra_diurna": horas_df["horas_extra_diurna"].sum(),
        "horas_extra_nocturna": horas_df["horas_extra_nocturna"].sum(),
        "horas_extra_dominical_festivo": horas_df["horas_extra_dominical_festivo"].sum(),
        "horas_extra_dominical_festivo_nocturna": horas_df["horas_extra_dominical_festivo_nocturna"].sum(),
        "horas_recargo_nocturno": horas_df["horas_recargo_nocturno"].sum(),
        "horas_recargo_dominical": horas_df["horas_recargo_dominical"].sum(),
        "horas_descuento": horas_df["horas_descuento"].sum(),
        "bonificacion": horas_df["bonificacion"].sum(),
        "deduccion": horas_df["deduccion"].sum(),
    }

    st.success(f"Se encontraron {len(horas_df)} registro(s) de horas para este empleado en el período ({dias_default} día(s) distintos).")

    with st.form("form_liquidacion"):
        dias = st.number_input("Días trabajados (para prorratear salario y auxilio)", min_value=0, max_value=31, value=int(dias_default))

        col1, col2 = st.columns(2)
        with col1:
            no_pension = st.checkbox("No descontar pensión")
            incapacidad = st.checkbox("Incapacidad")
            sin_auxilio = st.checkbox("No incluye auxilio de transporte")
        with col2:
            no_salud = st.checkbox("No descontar salud")
            maternidad = st.checkbox("Licencia de maternidad")

        st.subheader("Devengos y deducciones adicionales (no registrados en Horas)")
        col3, col4 = st.columns(2)
        with col3:
            bonificaciones_adicionales = st.number_input("Bonificaciones adicionales", min_value=0.0, step=10000.0)
            consumos = st.number_input("Consumos", min_value=0.0, step=10000.0)
            ahorros = st.number_input("Ahorros", min_value=0.0, step=10000.0)
        with col4:
            danos = st.number_input("Daños", min_value=0.0, step=10000.0)
            otros = st.number_input("Otros", min_value=0.0, step=10000.0)

        calcular = st.form_submit_button("🧮 Calcular liquidación")

    if calcular or "ultima_liquidacion" in st.session_state:
        extras = {
            "no_pension": no_pension, "no_salud": no_salud, "incapacidad": incapacidad,
            "maternidad": maternidad, "sin_auxilio": sin_auxilio,
            "bonificaciones_adicionales": bonificaciones_adicionales,
            "consumos": consumos, "danos": danos, "ahorros": ahorros, "otros": otros,
        }
        calculo = calcular_liquidacion(emp_row, horas_periodo, dias, extras)
        st.session_state["ultima_liquidacion"] = calculo

        st.divider()
        st.subheader("Resultado")
        colA, colB, colC = st.columns(3)
        colA.metric("Total devengado", pesos(calculo["devengado"]))
        colB.metric("Total deducciones", pesos(calculo["deducciones"]))
        colC.metric("Neto a pagar", pesos(calculo["neto"]))

        pdf_bytes = generar_pdf(emp_row, (fecha_inicio, fecha_fin), dias, horas_periodo, calculo)
        st.download_button(
            "⬇️ Descargar colilla de pago en PDF",
            data=pdf_bytes,
            file_name=f"liquidacion_{emp_row['nombre'].replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.pdf",
            mime="application/pdf"
        )
