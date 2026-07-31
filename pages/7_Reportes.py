import streamlit as st
import pandas as pd
from database import get_connection, get_multiplicadores, execute, read_sql_query

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("📊 Reportes")

with get_connection() as conn:
    empleados_df = read_sql_query("SELECT * FROM empleados", conn)
    horas_df = read_sql_query("""
        SELECT h.*, e.valor_hora, e.nombre AS empleado_nombre
        FROM horas h JOIN empleados e ON h.empleado_id = e.id
    """, conn)
    asistencia_df = read_sql_query("SELECT * FROM asistencia", conn)
    cancelaciones_df = read_sql_query("""
        SELECT c.*, e.nombre AS empleado_nombre
        FROM cancelaciones_contrato c JOIN empleados e ON c.empleado_id = e.id
    """, conn)

# ---------- CÁLCULO DEL VALOR DE NÓMINA (mismo criterio que el liquidador) ----------
m = get_multiplicadores()
total_nomina = 0.0
if not horas_df.empty:
    horas_df["pago_normales"] = horas_df["horas_normales"] * horas_df["valor_hora"]
    horas_df["pago_extra"] = (
        horas_df["horas_extra_diurna"] * horas_df["valor_hora"] * m["extra_diurna"]
        + horas_df["horas_extra_nocturna"] * horas_df["valor_hora"] * m["extra_nocturna"]
        + horas_df["horas_extra_dominical_festivo"] * horas_df["valor_hora"] * m["extra_dominical_festivo"]
        + horas_df["horas_extra_dominical_festivo_nocturna"] * horas_df["valor_hora"] * m["extra_dominical_festivo_nocturna"]
    )
    horas_df["pago_recargos"] = (
        horas_df["horas_recargo_nocturno"] * horas_df["valor_hora"] * m["recargo_nocturno"]
        + horas_df["horas_recargo_dominical"] * horas_df["valor_hora"] * m["recargo_dominical"]
    )
    horas_df["pago_descuento"] = horas_df["horas_descuento"] * horas_df["valor_hora"]
    horas_df["total_liquidado"] = (
        horas_df["pago_normales"] + horas_df["pago_extra"] + horas_df["pago_recargos"]
        + horas_df["bonificacion"] - horas_df["deduccion"] - horas_df["pago_descuento"]
    )
    total_nomina = horas_df["total_liquidado"].sum()

total_liquidaciones = cancelaciones_df["valor_liquidacion"].sum() if not cancelaciones_df.empty else 0.0
total_indemnizaciones = cancelaciones_df["valor_indemnizacion"].sum() if not cancelaciones_df.empty else 0.0

# ---------- MÉTRICAS GENERALES ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Empleados activos", int((empleados_df["estado"] == "Activo").sum()) if not empleados_df.empty else 0)
col2.metric("Empleados retirados", int((empleados_df["estado"] == "Inactivo").sum()) if not empleados_df.empty else 0)
col3.metric("Total nómina liquidada", f"${total_nomina:,.0f}")
col4.metric("Novedades de asistencia", len(asistencia_df))

st.divider()

st.subheader("Liquidaciones e indemnizaciones por cancelación de contrato")
col5, col6, col7 = st.columns(3)
col5.metric("Total liquidaciones", f"${total_liquidaciones:,.0f}")
col6.metric("Total indemnizaciones", f"${total_indemnizaciones:,.0f}")
col7.metric("Total pagado por retiros", f"${(total_liquidaciones + total_indemnizaciones):,.0f}")

st.divider()

if not horas_df.empty:
    st.subheader("Nómina liquidada por mes")
    horas_df["fecha_dt"] = pd.to_datetime(horas_df["fecha"])
    horas_df["mes"] = horas_df["fecha_dt"].dt.to_period("M").astype(str)
    resumen_mes = horas_df.groupby("mes")["total_liquidado"].sum().reset_index()
    st.bar_chart(resumen_mes, x="mes", y="total_liquidado")

    st.divider()
    st.subheader("Nómina liquidada por empleado")
    resumen_emp = horas_df.groupby("empleado_nombre")["total_liquidado"].sum().reset_index().sort_values("total_liquidado", ascending=False)
    st.dataframe(resumen_emp, use_container_width=True, hide_index=True)
else:
    st.info("Todavía no hay datos de horas registrados para mostrar tendencias de nómina.")

st.divider()

if not asistencia_df.empty:
    st.subheader("Novedades de asistencia por tipo")
    conteo = asistencia_df["tipo"].value_counts().reset_index()
    conteo.columns = ["tipo", "cantidad"]
    st.bar_chart(conteo, x="tipo", y="cantidad")

if not cancelaciones_df.empty:
    st.divider()
    st.subheader("Cancelaciones de contrato por motivo")
    st.dataframe(
        cancelaciones_df[["empleado_nombre", "fecha", "motivo", "valor_liquidacion", "valor_indemnizacion"]],
        use_container_width=True, hide_index=True
    )
