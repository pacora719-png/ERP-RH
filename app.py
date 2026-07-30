import streamlit as st
from database import init_db, get_config, set_config

st.set_page_config(page_title="ERP", page_icon="🏢", layout="wide")

init_db()
nombre_empresa = get_config("nombre_empresa", "Mi Empresa")


def check_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    st.title(f"🏢 {nombre_empresa}")
    st.subheader("Iniciar sesión")

    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")

    if enviar:
        # Usuarios y contraseñas se definen en st.secrets (ver README para configurarlos)
        usuarios_validos = st.secrets.get("usuarios", {"admin": "admin123"})
        if usuario in usuarios_validos and clave == usuarios_validos[usuario]:
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

    return False


if not check_login():
    st.stop()

st.sidebar.success(f"Sesión iniciada como: {st.session_state.usuario}")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.autenticado = False
    st.rerun()

st.title(f"🏢 {nombre_empresa}")
st.markdown("""
Usa el menú de la izquierda para navegar entre los módulos:

- ⏱️ **Horas y Nómina** — registro de horas trabajadas, extras, bonificaciones y deducciones
- 👥 **Empleados** — expedientes del personal
- 📅 **Asistencia** — vacaciones, permisos e incapacidades
- 📦 **Inventario** — control de insumos y stock
- ⚙️ **Configuración** — nombre de la empresa y ubicaciones/sedes
- 📊 **Reportes** — resumen general del negocio
""")

with st.expander("⚙️ Configurar nombre de la empresa"):
    nuevo_nombre = st.text_input("Nombre de la empresa", value=nombre_empresa)
    if st.button("Guardar nombre"):
        set_config("nombre_empresa", nuevo_nombre)
        st.success("Nombre actualizado.")
        st.rerun()
