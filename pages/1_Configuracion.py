import streamlit as st
import pandas as pd
from database import get_connection, get_config, set_config

st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("Por favor inicia sesión desde la página principal.")
    st.stop()

st.title("⚙️ Configuración")

st.subheader("Datos de la empresa")
nombre_empresa = get_config("nombre_empresa", "Mi Empresa")
nuevo_nombre = st.text_input("Nombre de la empresa", value=nombre_empresa)
if st.button("Guardar nombre de la empresa"):
    set_config("nombre_empresa", nuevo_nombre)
    st.success("Guardado.")
    st.rerun()

st.divider()

st.subheader("Ubicaciones / Sedes")
st.caption("Agrega las sedes o sucursales de tu empresa. Estas aparecerán como opción en Empleados e Inventario.")

with get_connection() as conn:
    df = pd.read_sql_query("SELECT * FROM ubicaciones ORDER BY nombre", conn)

if not df.empty:
    st.dataframe(df[["id", "nombre"]], use_container_width=True, hide_index=True)

col1, col2 = st.columns([3, 1])
with col1:
    nueva_ubicacion = st.text_input("Nueva ubicación / sede", key="nueva_ubicacion")
with col2:
    st.write("")
    st.write("")
    if st.button("➕ Agregar ubicación"):
        if nueva_ubicacion.strip():
            try:
                with get_connection() as conn:
                    conn.execute("INSERT INTO ubicaciones (nombre) VALUES (?)", (nueva_ubicacion.strip(),))
                st.success(f"Ubicación '{nueva_ubicacion}' agregada.")
                st.rerun()
            except Exception:
                st.error("Esa ubicación ya existe.")
        else:
            st.error("Escribe un nombre para la ubicación.")

if not df.empty:
    ubicacion_a_borrar = st.selectbox(
        "Eliminar una ubicación",
        df["id"].tolist(),
        format_func=lambda x: df[df["id"] == x]["nombre"].values[0]
    )
    if st.button("🗑️ Eliminar ubicación seleccionada"):
        with get_connection() as conn:
            conn.execute("DELETE FROM ubicaciones WHERE id=?", (int(ubicacion_a_borrar),))
        st.success("Ubicación eliminada.")
        st.rerun()
