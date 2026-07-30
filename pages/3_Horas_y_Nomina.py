import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
from database import get_connection, get_ubicaciones
from excel_utils import exportar_excel

st.set_page_config(page_title="Horas y Nómina", page_icon="⏱️", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("⏱️ Horas y Nómina")

with get_connection() as conn:
    empleados_df = pd.read_sql_query("SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn)

if empleados_df.empty:
    st.warning("No hay empleados activos. Ve a **Empleados** para agregar al menos uno.")
    st.stop()

tab_registrar, tab_historial = st.tabs(["➕ Registrar horas", "📋 Historial y nómina"])

# ---------- REGISTRAR ----------
with tab_registrar:
    empleado_id = st.selectbox(
        "Empleado",
        empleados_df["id"].tolist(),
        format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
    )
    valor_hora_default = float(empleados_df[empleados_df["id"] == empleado_id]["valor_hora"].values[0] or 0)

    with st.form("registrar_horas", clear_on_submit=True):
        fecha = st.date_input("Fecha")
        col1, col2 = st.columns(2)
        with col1:
            hora_entrada = st.time_input("Hora de entrada", value=time(8, 0))
        with col2:
            hora_salida = st.time_input("Hora de salida", value=time(17, 0))

        col3, col4 = st.columns(2)
        with col3:
            horas_extra = st.number_input("Horas extra", min_value=0.0, step=0.5)
        with col4:
            st.metric("Valor hora del empleado", f"${valor_hora_default:,.0f}")

        col5, col6 = st.columns(2)
        with col5:
            bonificacion = st.number_input("Bonificación", min_value=0.0, step=1000.0)
        with col6:
            deduccion = st.number_input("Deducción", min_value=0.0, step=1000.0)

        observacion = st.text_input("Observación (opcional)")
        guardar = st.form_submit_button("💾 Guardar registro")

    if guardar:
        entrada_dt = datetime.combine(fecha, hora_entrada)
        salida_dt = datetime.combine(fecha, hora_salida)
        horas_normales = max(0, (salida_dt - entrada_dt).total_seconds() / 3600)

        with get_connection() as conn:
            conn.execute("""
                INSERT INTO horas (empleado_id, fecha, hora_entrada, hora_salida, horas_normales,
                horas_extra, bonificacion, deduccion, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (int(empleado_id), str(fecha), str(hora_entrada), str(hora_salida),
                  round(horas_normales, 2), horas_extra, bonificacion, deduccion, observacion))
        st.success(f"Registro guardado: {round(horas_normales, 2)} horas normales + {horas_extra} horas extra.")

# ---------- HISTORIAL / NÓMINA ----------
with tab_historial:
    st.caption("Elige un rango de fechas, o usa el atajo de 'semana actual' / 'semana pasada'.")
    atajo = st.radio("Atajo rápido", ["Rango personalizado", "Semana actual", "Semana pasada"], horizontal=True)

    hoy = date.today()
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana

    if atajo == "Semana actual":
        fecha_inicio = inicio_semana_actual
        fecha_fin = inicio_semana_actual + timedelta(days=6)
    elif atajo == "Semana pasada":
        fecha_inicio = inicio_semana_actual - timedelta(days=7)
        fecha_fin = inicio_semana_actual - timedelta(days=1)
    else:
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Desde", key="hist_desde")
        with col2:
            fecha_fin = st.date_input("Hasta", key="hist_hasta")

    if atajo != "Rango personalizado":
        st.info(f"Mostrando del **{fecha_inicio}** al **{fecha_fin}**")

    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT h.*, e.nombre AS empleado_nombre, e.valor_hora
            FROM horas h JOIN empleados e ON h.empleado_id = e.id
            WHERE h.fecha BETWEEN ? AND ?
            ORDER BY h.fecha
        """, conn, params=(str(fecha_inicio), str(fecha_fin)))

    if df.empty:
        st.info("No hay registros de horas en ese rango de fechas.")
    else:
        df["pago_normales"] = df["horas_normales"] * df["valor_hora"]
        df["pago_extra"] = df["horas_extra"] * df["valor_hora"] * 1.25  # recargo del 25% para hora extra
        df["total_a_pagar"] = df["pago_normales"] + df["pago_extra"] + df["bonificacion"] - df["deduccion"]

        detalle_mostrar = df[["fecha", "empleado_nombre", "horas_normales", "horas_extra",
                               "bonificacion", "deduccion", "total_a_pagar"]]

        st.dataframe(detalle_mostrar, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Resumen de nómina por empleado")
        resumen = df.groupby("empleado_nombre").agg(
            horas_normales=("horas_normales", "sum"),
            horas_extra=("horas_extra", "sum"),
            bonificaciones=("bonificacion", "sum"),
            deducciones=("deduccion", "sum"),
            total_a_pagar=("total_a_pagar", "sum")
        ).reset_index()

        st.dataframe(resumen, use_container_width=True, hide_index=True)
        st.metric("Total nómina del período", f"${resumen['total_a_pagar'].sum():,.0f}")

        st.divider()
        nombre_archivo = f"horas_{fecha_inicio}_a_{fecha_fin}.xlsx"

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Descargar detalle diario en Excel",
                data=exportar_excel(detalle_mostrar, "Detalle horas"),
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_b:
            st.download_button(
                "⬇️ Descargar resumen de nómina en Excel",
                data=exportar_excel(resumen, "Resumen nómina"),
                file_name=f"resumen_{nombre_archivo}",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
