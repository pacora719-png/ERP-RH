import streamlit as st
import pandas as pd
from database import get_connection
from excel_utils import exportar_excel

st.set_page_config(page_title="Asistencia", page_icon="📅", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("📅 Asistencia")

with get_connection() as conn:
    empleados_df = pd.read_sql_query("SELECT * FROM empleados WHERE estado='Activo' ORDER BY nombre", conn)

if empleados_df.empty:
    st.warning("No hay empleados activos. Ve a **Empleados** para agregar al menos uno.")
    st.stop()

tab_registrar, tab_historial = st.tabs(["➕ Registrar novedad", "📋 Historial"])

with tab_registrar:
    with st.form("registrar_asistencia", clear_on_submit=True):
        empleado_id = st.selectbox(
            "Empleado",
            empleados_df["id"].tolist(),
            format_func=lambda x: empleados_df[empleados_df["id"] == x]["nombre"].values[0]
        )
        tipo = st.selectbox("Tipo", ["Vacaciones", "Permiso", "Incapacidad", "Ausencia injustificada"])
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin")
        comentario = st.text_area("Comentario (opcional)")
        guardar = st.form_submit_button("💾 Guardar")

    if guardar:
        if fecha_fin < fecha_inicio:
            st.error("La fecha fin no puede ser anterior a la fecha inicio.")
        else:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO asistencia (empleado_id, fecha_inicio, fecha_fin, tipo, comentario)
                    VALUES (?, ?, ?, ?, ?)
                """, (int(empleado_id), str(fecha_inicio), str(fecha_fin), tipo, comentario))
            st.success("Registro guardado.")

with tab_historial:
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT a.*, e.nombre AS empleado_nombre
            FROM asistencia a JOIN empleados e ON a.empleado_id = e.id
            ORDER BY a.fecha_inicio DESC
        """, conn)

    if df.empty:
        st.info("Todavía no hay novedades registradas.")
    else:
        tipo_filtro = st.selectbox("Filtrar por tipo", ["Todos"] + df["tipo"].unique().tolist())
        df_mostrar = df if tipo_filtro == "Todos" else df[df["tipo"] == tipo_filtro]

        st.dataframe(
            df_mostrar[["empleado_nombre", "tipo", "fecha_inicio", "fecha_fin", "comentario"]],
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar en Excel",
            data=exportar_excel(df_mostrar[["empleado_nombre", "tipo", "fecha_inicio", "fecha_fin", "comentario"]], "Asistencia"),
            file_name="asistencia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()
        registro_id = st.selectbox("Eliminar un registro", df["id"].tolist())
        if st.button("🗑️ Eliminar registro seleccionado"):
            with get_connection() as conn:
                conn.execute("DELETE FROM asistencia WHERE id=?", (int(registro_id),))
            st.success("Registro eliminado.")
            st.rerun()
