import streamlit as st
import pandas as pd
from database import get_connection, execute, read_sql_query
from excel_utils import exportar_excel

st.set_page_config(page_title="Cancelaciones de contrato", page_icon="📄", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("📄 Cancelaciones de contrato")

with get_connection() as conn:
    empleados_df = read_sql_query("SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn)

tab_registrar, tab_historial, tab_retirados = st.tabs(
    ["➕ Registrar cancelación", "📋 Historial de cancelaciones", "🚪 Empleados retirados"]
)

# ---------- REGISTRAR ----------
with tab_registrar:
    if empleados_df.empty:
        st.warning("No hay empleados activos para cancelar contrato.")
    else:
        with st.form("registrar_cancelacion", clear_on_submit=True):
            empleado_id = st.selectbox(
                "Empleado",
                empleados_df["id"].tolist(),
                format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
            )
            fecha = st.date_input("Fecha de cancelación")
            motivo = st.text_area("Motivo")
            col1, col2 = st.columns(2)
            with col1:
                valor_liquidacion = st.number_input("Valor liquidación", min_value=0.0, step=10000.0)
            with col2:
                valor_indemnizacion = st.number_input("Valor indemnización (si aplica)", min_value=0.0, step=10000.0)
            evidencia = st.file_uploader("Archivo de evidencia (opcional)", type=["pdf", "png", "jpg", "jpeg", "docx"])
            marcar_inactivo = st.checkbox("Marcar al empleado como Inactivo (retirado)", value=True)

            guardar = st.form_submit_button("💾 Guardar cancelación")

        if guardar:
            evidencia_nombre = evidencia.name if evidencia is not None else None
            evidencia_datos = evidencia.read() if evidencia is not None else None

            with get_connection() as conn:
                execute(conn, """
                    INSERT INTO cancelaciones_contrato
                    (empleado_id, fecha, motivo, valor_liquidacion, valor_indemnizacion, evidencia_nombre, evidencia_datos)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (int(empleado_id), str(fecha), motivo, valor_liquidacion, valor_indemnizacion,
                      evidencia_nombre, evidencia_datos))

                if marcar_inactivo:
                    execute(conn, "UPDATE empleados SET estado='Inactivo' WHERE id=?", (int(empleado_id),))

            st.success("Cancelación registrada correctamente.")
            st.rerun()

# ---------- HISTORIAL ----------
with tab_historial:
    with get_connection() as conn:
        df = read_sql_query("""
            SELECT c.id, c.fecha, c.motivo, c.valor_liquidacion, c.valor_indemnizacion,
                   c.evidencia_nombre, e.nombre AS empleado_nombre
            FROM cancelaciones_contrato c JOIN empleados e ON c.empleado_id = e.id
            ORDER BY c.fecha DESC
        """, conn)

    if df.empty:
        st.info("Todavía no hay cancelaciones de contrato registradas.")
    else:
        st.dataframe(
            df[["empleado_nombre", "fecha", "motivo", "valor_liquidacion", "valor_indemnizacion", "evidencia_nombre"]],
            use_container_width=True,
            hide_index=True
        )

        total_liquidaciones = df["valor_liquidacion"].sum()
        total_indemnizaciones = df["valor_indemnizacion"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Total liquidaciones", f"${total_liquidaciones:,.0f}")
        col2.metric("Total indemnizaciones", f"${total_indemnizaciones:,.0f}")

        st.download_button(
            "⬇️ Descargar en Excel",
            data=exportar_excel(df.drop(columns=["id"]), "Cancelaciones"),
            file_name="cancelaciones_contrato.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()
        st.subheader("Descargar evidencia")
        con_evidencia = df[df["evidencia_nombre"].notna()]
        if con_evidencia.empty:
            st.caption("Ninguna cancelación tiene archivo de evidencia adjunto.")
        else:
            registro_id = st.selectbox(
                "Selecciona un registro",
                con_evidencia["id"].tolist(),
                format_func=lambda x: f"{con_evidencia[con_evidencia['id']==x]['empleado_nombre'].values[0]} - {con_evidencia[con_evidencia['id']==x]['evidencia_nombre'].values[0]}"
            )
            with get_connection() as conn:
                fila = execute(conn, 
                    "SELECT evidencia_nombre, evidencia_datos FROM cancelaciones_contrato WHERE id=?",
                    (int(registro_id),)
                ).fetchone()
            if fila and fila["evidencia_datos"]:
                st.download_button(
                    "⬇️ Descargar evidencia",
                    data=fila["evidencia_datos"],
                    file_name=fila["evidencia_nombre"]
                )

        st.divider()
        registro_a_borrar = st.selectbox(
            "Eliminar un registro de cancelación",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["empleado_nombre"].values[0],
            key="borrar_cancelacion"
        )
        if st.button("🗑️ Eliminar registro seleccionado"):
            with get_connection() as conn:
                execute(conn, "DELETE FROM cancelaciones_contrato WHERE id=?", (int(registro_a_borrar),))
            st.success("Registro eliminado.")
            st.rerun()

# ---------- EMPLEADOS RETIRADOS ----------
with tab_retirados:
    with get_connection() as conn:
        retirados_df = read_sql_query("""
            SELECT e.nombre, e.identificacion, e.cargo, e.fecha_ingreso,
                   u.nombre AS ubicacion_nombre
            FROM empleados e LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id
            WHERE e.estado='Inactivo'
            ORDER BY e.nombre
        """, conn)

    if retirados_df.empty:
        st.info("No hay empleados retirados por el momento.")
    else:
        st.dataframe(retirados_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Descargar lista de retirados en Excel",
            data=exportar_excel(retirados_df, "Empleados retirados"),
            file_name="empleados_retirados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
