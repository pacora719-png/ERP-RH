import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("📊 Reportes")

with get_connection() as conn:
    empleados_df = pd.read_sql_query("SELECT * FROM empleados", conn)
    horas_df = pd.read_sql_query("SELECT * FROM horas", conn)
    asistencia_df = pd.read_sql_query("SELECT * FROM asistencia", conn)
    inventario_df = pd.read_sql_query("SELECT * FROM inventario", conn)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Empleados activos", int((empleados_df["estado"] == "Activo").sum()) if not empleados_df.empty else 0)
col2.metric("Registros de horas", len(horas_df))
col3.metric("Novedades de asistencia", len(asistencia_df))
col4.metric("Productos en inventario", len(inventario_df))

st.divider()

if not horas_df.empty:
    horas_df["pago_normales"] = horas_df["horas_normales"] * 0  # se recalcula abajo con valor_hora real
    with get_connection() as conn:
        detalle = pd.read_sql_query("""
            SELECT h.fecha, h.horas_normales, h.horas_extra, h.bonificacion, h.deduccion, e.valor_hora
            FROM horas h JOIN empleados e ON h.empleado_id = e.id
        """, conn)
    detalle["total"] = (detalle["horas_normales"] * detalle["valor_hora"]
                         + detalle["horas_extra"] * detalle["valor_hora"] * 1.25
                         + detalle["bonificacion"] - detalle["deduccion"])
    detalle["fecha"] = pd.to_datetime(detalle["fecha"])
    detalle["mes"] = detalle["fecha"].dt.to_period("M").astype(str)

    st.subheader("Costo de nómina por mes")
    resumen_mes = detalle.groupby("mes")["total"].sum().reset_index()
    st.bar_chart(resumen_mes, x="mes", y="total")
else:
    st.info("Todavía no hay datos de horas registrados para mostrar tendencias de nómina.")

st.divider()

if not inventario_df.empty:
    st.subheader("Productos con stock bajo")
    bajos = inventario_df[inventario_df["stock_actual"] <= inventario_df["stock_minimo"]]
    if bajos.empty:
        st.success("Ningún producto está por debajo del stock mínimo.")
    else:
        st.dataframe(bajos[["nombre", "stock_actual", "stock_minimo"]], use_container_width=True, hide_index=True)

st.divider()

if not asistencia_df.empty:
    st.subheader("Novedades por tipo")
    conteo = asistencia_df["tipo"].value_counts().reset_index()
    conteo.columns = ["tipo", "cantidad"]
    st.bar_chart(conteo, x="tipo", y="cantidad")
